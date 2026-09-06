"""Letting a visitor nominate their own phone as this session's safe-dial target.

The whole point of safe dial is that the set of reachable numbers is decided by the server,
not by whoever is holding the URL. This module widens that set by exactly one number per
session, and only after the number has proved it belongs to the person asking.

The proof is a call. The agent rings the number once, reads a four-digit code, and hangs up.
Until that code comes back, the number receives nothing else. That single call is the one
place in the product where we dial a number nobody has vouched for, so it is rate-limited
per number and per session, gated behind a feature flag that refuses to arm without an
access code, and written to an audit trail.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.core.config import Settings
from app.core.db import Db, as_doc
from app.core.errors import AppError, FeatureDisabled, NotFound, ValidationFailed
from app.core.models import new_id, utcnow
from app.core.phone import assert_dialable, mask, normalize_phone, pretty
from app.integrations.hunar.client import HunarClient
from app.integrations.hunar.schemas import (
    EARLIEST_CALL_TIME,
    LATEST_CALL_TIME,
    Guardrails,
    HunarAgentCreate,
    HunarCallCreate,
    next_window_opens,
    within_calling_window,
)

log = structlog.get_logger()

VERIFY_AGENT_KEY = "dial_verify_agent"
# The widest window Hunar will accept. It is not "any time": 00:00 is rejected outright.
WIDEST_WINDOW = Guardrails(
    allowed_days=["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
    earliest_call_time=EARLIEST_CALL_TIME,
    last_call_time=LATEST_CALL_TIME,
)


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"


class VerificationFailed(AppError):
    status_code = 400
    code = "verification_failed"


class OutsideCallingWindow(AppError):
    """Hunar would accept the call and hold it until morning, which is useless here.

    A screening call is happy to wait. A verification call is not: someone is sitting in
    front of the form waiting to type a code that expires in minutes, so a call placed now
    would arrive long after the code did, having spent one of the day's slots for nothing.
    """

    status_code = 409
    code = "outside_calling_window"


def _require_enabled(settings: Settings) -> None:
    if not settings.allow_client_dial_target:
        raise FeatureDisabled("This deployment does not accept browser-supplied numbers.")
    if not settings.client_dial_enabled:
        raise FeatureDisabled(
            settings.client_dial_blocked_reason or "Client dialling is not configured."
        )


async def _verify_agent_id(db: Db, hunar: HunarClient) -> str:
    """The agent that reads a code aloud. Created once, then remembered.

    Kept deliberately narrow: it says the code and ends. It never asks a question, so a
    verification call cannot be turned into a conversation with a stranger.
    """
    doc = await db.app_meta.find_one({"_id": VERIFY_AGENT_KEY})
    if doc and doc.get("hunar_agent_id"):
        return str(doc["hunar_agent_id"])

    agent = await hunar.create_agent(
        HunarAgentCreate(
            name="Ringside verification",
            language="ENGLISH",
            voice_persona="NEHA",
            persona_name="Neha",
            introduction=("Hello, this is Ringside with the verification code you just requested."),
            objective="Read a verification code aloud and end the call.",
            agent_prompt=(
                "You are {persona_name} from Ringside. Say exactly this and nothing else: "
                "'Your Ringside verification code is {code}.' Then read the code once more, "
                "digit by digit and slowly. Then say 'goodbye' and end the call. Do not ask "
                "questions, do not answer questions, and do not discuss anything else. If the "
                "person speaks, repeat the code once and end the call."
            ),
            result_prompt=(
                'Return {"delivered": "yes"} if the code was read aloud, otherwise '
                '{"delivered": "no"}.'
            ),
            result_schema={"delivered": "string"},
        )
    )
    await db.app_meta.update_one(
        {"_id": VERIFY_AGENT_KEY},
        {"$set": {"hunar_agent_id": agent.id, "created_at": utcnow()}},
        upsert=True,
    )
    log.info("verify_agent_created", hunar_agent_id=agent.id)
    return agent.id


async def calls_left_today(db: Db, settings: Settings, session_id: str | None) -> int:
    """The binding allowance: the lowest of the limits that do not depend on the phone typed.

    Shown in the UI, so it must never promise more than the next request would actually
    allow. The per-number rule is deliberately excluded: it depends on a number the visitor
    has not entered yet, and quoting it would need a lookup on every keystroke. The form
    states that rule in words instead.
    """
    since = utcnow() - timedelta(days=1)
    used_globally = await db.dial_targets.count_documents({"created_at": {"$gte": since}})
    left = max(settings.dial_verify_global_per_day - used_globally, 0)
    if session_id:
        used = await db.dial_targets.count_documents(
            {"session_id": session_id, "created_at": {"$gte": since}}
        )
        left = min(left, max(settings.dial_verify_per_session_per_day - used, 0))
    return left


async def _assert_within_limits(db: Db, settings: Settings, phone: str, session_id: str) -> None:
    """Three caps, broadest first, so the refusal names the one that will still apply.

    Checking the number first would say "try another number" when the whole demo is at
    capacity and no other number would work either.
    """
    since = utcnow() - timedelta(days=1)
    used_globally = await db.dial_targets.count_documents({"created_at": {"$gte": since}})
    if used_globally >= settings.dial_verify_global_per_day:
        raise RateLimited(
            "This demo has placed all of today's verification calls. Try again tomorrow."
        )
    per_number = await db.dial_targets.count_documents(
        {"phone": phone, "created_at": {"$gte": since}}
    )
    if per_number >= settings.dial_verify_per_number_per_day:
        raise RateLimited(
            f"That number has been sent {per_number} verification calls today. Try tomorrow."
        )
    per_session = await db.dial_targets.count_documents(
        {"session_id": session_id, "created_at": {"$gte": since}}
    )
    if per_session >= settings.dial_verify_per_session_per_day:
        raise RateLimited("This browser has requested too many verification calls today.")


async def start_verification(
    db: Db,
    hunar: HunarClient,
    settings: Settings,
    *,
    phone_raw: str,
    consent: bool,
    session_id: str,
) -> dict[str, Any]:
    _require_enabled(settings)
    if not consent:
        raise ValidationFailed("Confirm the number is yours before we call it.")

    phone = normalize_phone(phone_raw)
    if not phone:
        raise ValidationFailed("Enter a phone number.")
    assert_dialable(phone)

    # Checked before the limits, so a request that could never ring costs nothing.
    if not within_calling_window(settings.hunar_timezone):
        opens = next_window_opens(settings.hunar_timezone)
        raise OutsideCallingWindow(
            f"Hunar only places calls between {EARLIEST_CALL_TIME} and {LATEST_CALL_TIME} "
            f"({settings.hunar_timezone}). The next one can ring at "
            f"{opens.strftime('%H:%M on %d %b')}."
        )

    await _assert_within_limits(db, settings, phone, session_id)

    code = f"{secrets.randbelow(9000) + 1000}"
    now = utcnow()
    doc: dict[str, Any] = {
        "_id": new_id(),
        "session_id": session_id,
        "phone": phone,
        "code": code,
        "attempts": 0,
        "verified_at": None,
        "expires_at": now + timedelta(minutes=settings.dial_code_ttl_minutes),
        "created_at": now,
        "hunar_call_id": None,
    }
    await db.dial_targets.insert_one(doc)

    # The one call in the product that reaches a number nobody has vouched for yet.
    #
    # The row is written before the call so the code exists if the callback beats us back,
    # which means a call Hunar refuses would otherwise leave a row that spends a slot against
    # the daily caps. Nobody heard a code, so it is not a verification; drop it and let the
    # visitor try again.
    try:
        agent_id = await _verify_agent_id(db, hunar)
        created = await hunar.create_call(
            HunarCallCreate(
                agent_id=agent_id,
                callee_name="Ringside verification",
                mobile_number=phone,
                custom_data={"code": " ".join(code)},
                request_id=f"verify-{doc['_id'][:8]}",
                timezone=settings.hunar_timezone,
                guardrails=WIDEST_WINDOW,
            )
        )
    except Exception:
        await db.dial_targets.delete_one({"_id": doc["_id"]})
        raise
    await db.dial_targets.update_one({"_id": doc["_id"]}, {"$set": {"hunar_call_id": created.id}})
    await audit(
        db,
        action="verify_call_placed",
        phone=phone,
        session_id=session_id,
        detail={"dialTargetId": doc["_id"], "hunarCallId": created.id},
    )
    log.info("dial_verify_started", phone=mask(phone), session=session_id[:8])
    return doc


async def confirm_verification(
    db: Db, settings: Settings, *, target_id: str, code: str, session_id: str
) -> dict[str, Any]:
    _require_enabled(settings)
    raw = await db.dial_targets.find_one({"_id": target_id, "session_id": session_id})
    if not raw:
        raise NotFound("No verification in progress for this browser.")
    doc = as_doc(raw)

    expires = doc["expires_at"]
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if datetime.now(UTC) > expires:
        raise VerificationFailed("That code has expired. Request a new call.")

    if doc["attempts"] >= settings.dial_code_max_attempts:
        raise RateLimited("Too many wrong codes. Request a new call.")

    if code.strip() != doc["code"]:
        await db.dial_targets.update_one({"_id": target_id}, {"$inc": {"attempts": 1}})
        left = settings.dial_code_max_attempts - (doc["attempts"] + 1)
        raise VerificationFailed(f"That code is not right. {max(left, 0)} attempts left.")

    now = utcnow()
    await db.dial_targets.update_one(
        {"_id": target_id},
        {
            "$set": {
                "verified_at": now,
                "expires_at": now + timedelta(hours=settings.dial_target_ttl_hours),
            }
        },
    )
    await audit(
        db,
        action="dial_target_verified",
        phone=doc["phone"],
        session_id=session_id,
        detail={"dialTargetId": target_id},
    )
    log.info("dial_target_verified", phone=mask(doc["phone"]), session=session_id[:8])
    return as_doc(await db.dial_targets.find_one({"_id": target_id}) or {})


async def current_target(db: Db, session_id: str) -> dict[str, Any] | None:
    """The verified, unexpired number this browser may ring, if any."""
    raw = await db.dial_targets.find_one(
        {"session_id": session_id, "verified_at": {"$ne": None}}, sort=[("verified_at", -1)]
    )
    if not raw:
        return None
    doc = as_doc(raw)
    expires = doc["expires_at"]
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return doc if datetime.now(UTC) <= expires else None


async def release_target(db: Db, session_id: str) -> None:
    await db.dial_targets.update_many(
        {"session_id": session_id, "verified_at": {"$ne": None}},
        {"$set": {"expires_at": utcnow()}},
    )


async def audit(
    db: Db, *, action: str, phone: str, session_id: str, detail: dict[str, Any] | None = None
) -> None:
    """Every number this product rings leaves a row, with where the number came from."""
    await db.dial_audit.insert_one(
        {
            "_id": new_id(),
            "at": utcnow(),
            "action": action,
            "phone": phone,
            "phone_masked": mask(phone),
            "session_id": session_id,
            "detail": detail or {},
        }
    )


def to_dto(doc: dict[str, Any] | None, settings: Settings) -> dict[str, Any] | None:
    if not doc:
        return None
    return {
        "id": doc["_id"],
        "phone_masked": mask(doc["phone"]),
        "phone_pretty": pretty(doc["phone"]) if doc.get("verified_at") else None,
        "verified": doc.get("verified_at") is not None,
        "expires_at": doc.get("expires_at"),
        "attempts_left": max(settings.dial_code_max_attempts - doc.get("attempts", 0), 0),
    }

"""Calls: launch through Hunar, keep our mirror in sync (webhooks + poller), enrich with LLM."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.core.config import Settings
from app.core.db import Db, as_doc
from app.core.errors import (
    AgentNotFound,
    CallNotFound,
    FeatureDisabled,
    HunarApiError,
    LlmError,
    ValidationFailed,
)
from app.core.events import EventBus
from app.core.models import new_id, parse_upstream_dt, utcnow
from app.core.pagination import Page
from app.integrations.hunar.client import HunarClient
from app.integrations.hunar.schemas import (
    TERMINAL_LIFECYCLE,
    CallbackConfig,
    Guardrails,
    HunarCall,
    HunarCallCreate,
    RetryConfig,
)
from app.integrations.llm.client import LlmService
from app.modules.calls.schemas import (
    CallDto,
    LaunchCallsRequest,
    LaunchCallsResponse,
    SkippedCandidateDto,
)
from app.modules.dial.service import audit as dial_audit
from app.modules.jobs.service import get_job_doc, job_for_llm

log = structlog.get_logger()

_UNKNOWN = {"", "unknown", "not available", "n/a", "none", "null"}


# ---------- dialling ----------


def resolve_dial_number(
    candidate: dict[str, Any], settings: Settings, *, verified_target: str | None = None
) -> tuple[str, bool, str]:
    """Decide what actually rings. Returns (number, is_safe_dial, source).

    Two ways a number becomes reachable, in order of precedence:

      real     the candidate's own number, only when safe dial is off globally AND that
               candidate was explicitly cleared in the UI
      session  a number this visitor proved is theirs by answering a verification call

    There is deliberately no third way. An operator-configured test number used to sit
    underneath these as a fallback, which meant the deployment had a privileged destination
    nobody had proved, and the demo worked for whoever set the variable and silently skipped
    for everyone else. Now the only phone a safe-dialled call can reach belongs to the person
    who asked for it.
    """
    real_allowed = (not settings.safe_dial_mode) and bool(candidate.get("allow_real_dial"))
    if real_allowed:
        if not candidate.get("phone"):
            raise ValidationFailed("Candidate has no phone number")
        return str(candidate["phone"]), False, "real"

    if verified_target:
        return verified_target, True, "session"

    raise ValidationFailed(
        "Verify your own number first — safe dial only rings a phone someone has proved "
        "is theirs, and the candidate's own number is never used."
    )


def build_custom_data(
    agent_vars: list[str], job: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, str]:
    defaults = {
        "candidate_name": candidate.get("name") or "there",
        "job_role": job.get("title") or "the role",
        "company": job.get("company") or "our company",
        "location": job.get("location") or candidate.get("location") or "your city",
        "job_title": job.get("title") or "the role",
        "company_name": job.get("company") or "our company",
    }
    out: dict[str, str] = {}
    for var in agent_vars:
        if var in defaults:
            out[var] = str(defaults[var])
        elif job.get(var) not in (None, "", []):
            out[var] = str(job[var])
        elif candidate.get(var) not in (None, "", []):
            out[var] = str(candidate[var])
        else:
            out[var] = ""
    return out


def _callback_config(settings: Settings) -> CallbackConfig | None:
    if not settings.webhooks_enabled:
        return None
    url = settings.public_base_url.rstrip("/") + "/webhooks/hunar"
    return CallbackConfig(
        call_status_callback_url=url,
        call_recording_callback_url=url,
        call_result_callback_url=url,
        call_summary_callback_url=url,
    )


async def launch_calls(
    db: Db,
    hunar: HunarClient,
    settings: Settings,
    body: LaunchCallsRequest,
    *,
    verified_target: str | None = None,
    session_id: str | None = None,
) -> LaunchCallsResponse:
    if not settings.hunar_enabled and settings.env != "test":
        raise FeatureDisabled("HUNAR_API_KEY is not configured.")
    job = await get_job_doc(db, body.job_id)
    agent_id = body.agent_id or job.get("agent_id")
    if not agent_id:
        raise ValidationFailed("This job has no screening agent yet. Create or select one first.")
    agent_raw = await db.agents.find_one({"_id": agent_id})
    if not agent_raw:
        raise AgentNotFound(f"Agent {agent_id} not found")
    agent = as_doc(agent_raw)

    calls: list[CallDto] = []
    skipped: list[SkippedCandidateDto] = []
    for cid in body.candidate_ids:
        candidate_raw = await db.candidates.find_one({"_id": cid, "job_id": body.job_id})
        if not candidate_raw:
            skipped.append(
                SkippedCandidateDto(candidate_id=cid, reason="candidate not found for this job")
            )
            continue
        candidate = as_doc(candidate_raw)
        # One call at a time per candidate. Picking a finished candidate again is allowed, a
        # second screen is a real thing; a second call while the first is still scheduled,
        # ringing or mid-conversation never is, and the table cannot be trusted to prevent it.
        active = await db.calls.find_one(
            {"candidate_id": cid, "lifecycle_status": {"$nin": list(TERMINAL_LIFECYCLE)}},
            {"_id": 1},
        )
        if active:
            skipped.append(
                SkippedCandidateDto(
                    candidate_id=cid, reason="a call is already in flight for this candidate"
                )
            )
            continue
        try:
            dialed, safe, dial_source = resolve_dial_number(
                candidate, settings, verified_target=verified_target
            )
        except ValidationFailed as exc:
            skipped.append(SkippedCandidateDto(candidate_id=cid, reason=exc.message))
            continue
        custom_data = build_custom_data(agent.get("custom_variables", []), job, candidate)
        request_id = f"hh-{cid[:8]}-{new_id()[:8]}"
        try:
            created = await hunar.create_call(
                HunarCallCreate(
                    agent_id=agent["hunar_agent_id"],
                    callee_name=candidate["name"],
                    mobile_number=dialed,
                    custom_data=custom_data,
                    request_id=request_id,
                    timezone=settings.hunar_timezone,
                    retry_config=RetryConfig(**body.retry.model_dump()),
                    guardrails=Guardrails(**body.guardrails.model_dump()),
                    callback_config=_callback_config(settings),
                )
            )
        except HunarApiError as exc:
            skipped.append(SkippedCandidateDto(candidate_id=cid, reason=f"Hunar: {exc.message}"))
            continue
        now = utcnow()
        doc: dict[str, Any] = {
            "_id": new_id(),
            "hunar_call_id": created.id,
            "request_id": created.request_id or request_id,
            "job_id": body.job_id,
            "candidate_id": cid,
            "agent_id": agent_id,
            "hunar_agent_id": agent["hunar_agent_id"],
            "callee_name": candidate["name"],
            "target_number": candidate.get("phone"),
            "dialed_number": dialed,
            "safe_dial": safe,
            "dial_source": dial_source,
            "custom_data": custom_data,
            "status": created.status,
            "lifecycle_status": "NOT_STARTED" if created.status == "NOT_STARTED" else "IN_PROGRESS",
            "engagement_status": None,
            "answered_by": None,
            "call_ended_by": None,
            "duration_seconds": None,
            "user_speech_duration": None,
            "recording_url": None,
            "result": {},
            "transcript": None,
            "assessment": None,
            "retry_count": 0,
            "retries_left": body.retry.max_retry_count,
            "next_retry_scheduled_at": None,
            "started_at": None,
            "ended_at": None,
            "last_synced_at": None,
            "events": [
                {
                    "at": now,
                    "kind": "created",
                    "status": created.status,
                    "source": "app",
                    "note": None,
                }
            ],
            "created_at": now,
            "updated_at": now,
        }
        await db.calls.insert_one(doc)
        await dial_audit(
            db,
            action="screening_call_placed",
            phone=dialed,
            session_id=session_id or "server",
            detail={"callId": doc["_id"], "source": dial_source, "candidateId": cid},
        )
        await db.candidates.update_one(
            {"_id": cid},
            {
                "$set": {
                    "latest_call_id": doc["_id"],
                    "latest_call_status": created.status,
                    "updated_at": now,
                }
            },
        )
        calls.append(CallDto.model_validate(doc))
    if calls:
        await db.jobs.update_one(
            {"_id": body.job_id}, {"$set": {"status": "active", "updated_at": utcnow()}}
        )
    return LaunchCallsResponse(calls=calls, skipped=skipped)


# ---------- syncing ----------


def apply_upstream(doc: dict[str, Any], hc: HunarCall, *, source: str) -> dict[str, Any]:
    """Compute the $set patch that brings our mirror in line with the upstream call."""
    now = utcnow()
    patch: dict[str, Any] = {
        "status": hc.status,
        "lifecycle_status": hc.lifecycle_status,
        "engagement_status": hc.engagement_status if hc.engagement_status != "-" else None,
        "answered_by": hc.answered_by if hc.answered_by != "-" else None,
        "call_ended_by": hc.call_ended_by if hc.call_ended_by != "-" else None,
        "duration_seconds": hc.duration_seconds,
        "user_speech_duration": hc.user_speech_duration,
        "recording_url": hc.recording_url or doc.get("recording_url"),
        "result": hc.result or doc.get("result") or {},
        "retry_count": hc.retry_count,
        "retries_left": hc.retries_left,
        "next_retry_scheduled_at": parse_upstream_dt(hc.next_retry_scheduled_at),
        "started_at": parse_upstream_dt(hc.started_at),
        "ended_at": parse_upstream_dt(hc.ended_at),
        "last_synced_at": now,
        "updated_at": now,
    }
    events = list(doc.get("events") or [])
    if hc.status != doc.get("status"):
        events.append(
            {"at": now, "kind": "status", "status": hc.status, "source": source, "note": None}
        )
    if hc.recording_url and not doc.get("recording_url"):
        events.append(
            {"at": now, "kind": "recording", "status": None, "source": source, "note": None}
        )
    if hc.result and not doc.get("result"):
        events.append({"at": now, "kind": "result", "status": None, "source": source, "note": None})
    patch["events"] = events
    return patch


def needs_sync(doc: dict[str, Any]) -> bool:
    if doc.get("lifecycle_status") not in TERMINAL_LIFECYCLE:
        return True
    # Terminal but still waiting for the recording/result to land (they arrive a little later).
    if doc.get("lifecycle_status") == "COMPLETED" and (
        not doc.get("result") or not doc.get("recording_url")
    ):
        ended = doc.get("ended_at") or doc.get("updated_at") or doc.get("created_at")
        if isinstance(ended, datetime):
            if ended.tzinfo is None:
                ended = ended.replace(tzinfo=UTC)
            return datetime.now(UTC) - ended < timedelta(minutes=15)
    return False


def _has_usable_result(result: dict[str, Any]) -> bool:
    return any(str(v).strip().lower() not in _UNKNOWN for v in result.values())


async def _after_sync(db: Db, llm: LlmService, doc: dict[str, Any]) -> None:
    """Cheap enrichment: assess once a usable result exists."""
    if doc.get("assessment") or not _has_usable_result(doc.get("result") or {}):
        return
    try:
        await assess_call(db, llm, doc["_id"])
    except (LlmError, Exception) as exc:  # never let enrichment break a sync
        log.warning("assess_failed", call_id=doc["_id"], error=str(exc)[:200])


def _announce(bus: EventBus | None, doc: dict[str, Any], before: dict[str, Any]) -> None:
    """Tell listeners a call moved. Silence when nothing did, so a quiet poll stays quiet."""
    if bus is None:
        return
    watched = ("status", "lifecycle_status", "engagement_status", "recording_url")
    changed = [k for k in watched if before.get(k) != doc.get(k)]
    if before.get("result") != doc.get("result"):
        changed.append("result")
    if not changed:
        return
    bus.publish(
        "call.updated",
        {
            "callId": doc["_id"],
            "jobId": doc.get("job_id"),
            "candidateId": doc.get("candidate_id"),
            "status": doc.get("status"),
            "lifecycleStatus": doc.get("lifecycle_status"),
            "changed": changed,
        },
    )


async def sync_call(
    db: Db,
    hunar: HunarClient,
    llm: LlmService,
    call_id: str,
    *,
    source: str = "poll",
    bus: EventBus | None = None,
) -> CallDto:
    doc = await get_call_doc(db, call_id)
    hc = await hunar.get_call(doc["hunar_call_id"])
    patch = apply_upstream(doc, hc, source=source)
    await db.calls.update_one({"_id": call_id}, {"$set": patch})
    await db.candidates.update_one(
        {"_id": doc["candidate_id"]},
        {"$set": {"latest_call_status": hc.status, "updated_at": utcnow()}},
    )
    fresh = await get_call_doc(db, call_id)
    _announce(bus, fresh, doc)
    await _after_sync(db, llm, fresh)
    return CallDto.model_validate(await get_call_doc(db, call_id))


async def sync_pending(
    db: Db,
    hunar: HunarClient,
    llm: LlmService,
    *,
    limit: int = 50,
    bus: EventBus | None = None,
) -> tuple[int, int]:
    q = {
        "$or": [
            {"lifecycle_status": {"$nin": list(TERMINAL_LIFECYCLE)}},
            {"lifecycle_status": "COMPLETED", "$or": [{"result": {}}, {"recording_url": None}]},
        ]
    }
    docs = [as_doc(d) for d in await db.calls.find(q).sort("updated_at", 1).to_list(length=limit)]
    synced = errors = 0
    for doc in docs:
        if not needs_sync(doc):
            continue
        try:
            await sync_call(db, hunar, llm, doc["_id"], source="poll", bus=bus)
            synced += 1
        except Exception as exc:
            errors += 1
            log.warning("sync_failed", call_id=doc["_id"], error=str(exc)[:200])
    return synced, errors


async def apply_webhook(
    db: Db, llm: LlmService, payload: dict[str, Any], *, bus: EventBus | None = None
) -> str | None:
    """Apply a webhook event to our mirror. Returns our call id if matched."""
    hunar_call_id = payload.get("call_id") or payload.get("id")
    if not hunar_call_id:
        return None
    raw = await db.calls.find_one({"hunar_call_id": hunar_call_id})
    if not raw:
        return None
    doc = as_doc(raw)
    now = utcnow()
    event_type = str(payload.get("event_type") or "unknown")
    patch: dict[str, Any] = {"updated_at": now, "last_synced_at": now}
    events = list(doc.get("events") or [])
    for key in (
        "status",
        "lifecycle_status",
        "retry_count",
        "retries_left",
        "engagement_status",
        "answered_by",
        "call_ended_by",
        "duration_seconds",
        "user_speech_duration",
    ):
        if payload.get(key) is not None:
            patch[key] = payload[key]
    if payload.get("next_retry_scheduled_at"):
        patch["next_retry_scheduled_at"] = parse_upstream_dt(payload["next_retry_scheduled_at"])
    if payload.get("recording_url"):
        patch["recording_url"] = payload["recording_url"]
    if isinstance(payload.get("result"), dict) and payload["result"]:
        patch["result"] = payload["result"]
    events.append(
        {
            "at": now,
            "kind": event_type,
            "status": payload.get("status"),
            "source": "webhook",
            "note": None,
        }
    )
    patch["events"] = events
    await db.calls.update_one({"_id": doc["_id"]}, {"$set": patch})
    if patch.get("status"):
        await db.candidates.update_one(
            {"_id": doc["candidate_id"]},
            {"$set": {"latest_call_status": patch["status"], "updated_at": now}},
        )
    fresh = await get_call_doc(db, doc["_id"])
    _announce(bus, fresh, doc)
    await _after_sync(db, llm, fresh)
    return str(doc["_id"])


# ---------- enrichment ----------


async def assess_call(db: Db, llm: LlmService, call_id: str) -> CallDto:
    doc = await get_call_doc(db, call_id)
    job = await get_job_doc(db, doc["job_id"])
    transcript = (doc.get("transcript") or {}).get("text") if doc.get("transcript") else None
    assessment = await llm.assess_call(job_for_llm(job), doc.get("result") or {}, transcript)
    await db.calls.update_one(
        {"_id": call_id},
        {
            "$set": {
                "assessment": assessment.model_dump(),
                "updated_at": utcnow(),
            }
        },
    )
    return CallDto.model_validate(await get_call_doc(db, call_id))


async def transcribe_call(db: Db, llm: LlmService, call_id: str) -> CallDto:
    doc = await get_call_doc(db, call_id)
    if not doc.get("recording_url"):
        raise ValidationFailed("This call has no recording yet.")
    transcript = await llm.transcribe(doc["recording_url"])
    await db.calls.update_one(
        {"_id": call_id}, {"$set": {"transcript": transcript.model_dump(), "updated_at": utcnow()}}
    )
    return CallDto.model_validate(await get_call_doc(db, call_id))


# ---------- queries ----------


async def get_call_doc(db: Db, call_id: str) -> dict[str, Any]:
    doc = await db.calls.find_one({"_id": call_id})
    if not doc:
        raise CallNotFound(f"Call {call_id} not found")
    return as_doc(doc)


async def get_call(db: Db, call_id: str) -> CallDto:
    return CallDto.model_validate(await get_call_doc(db, call_id))


async def list_calls(
    db: Db,
    *,
    job_id: str | None,
    candidate_id: str | None,
    statuses: list[str] | None,
    page: int,
    page_size: int,
) -> Page[CallDto]:
    q: dict[str, Any] = {}
    if job_id:
        q["job_id"] = job_id
    if candidate_id:
        q["candidate_id"] = candidate_id
    if statuses:
        q["status"] = {"$in": statuses}
    total = await db.calls.count_documents(q)
    docs = (
        await db.calls.find(q)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list(length=page_size)
    )
    return Page[CallDto](
        items=[CallDto.model_validate(d) for d in docs], total=total, page=page, page_size=page_size
    )

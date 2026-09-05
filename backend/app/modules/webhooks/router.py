"""Inbound Hunar webhooks. Not behind the access code (Hunar can't send it); HMAC-verified."""

from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, Request, Response

from app.core.deps import ContainerDep
from app.core.models import ApiModel, new_id, utcnow
from app.integrations.hunar.webhook import verify_signature
from app.modules.calls import service as calls

log = structlog.get_logger()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookAck(ApiModel):
    received: bool
    matched: bool
    signature_valid: bool


@router.post("/hunar", response_model=WebhookAck)
async def hunar_webhook(request: Request, c: ContainerDep, response: Response) -> WebhookAck:
    body = await request.body()
    sig_ok = verify_signature(
        c.settings.hunar_api_key,
        request.headers.get("X-Hunar-Timestamp"),
        request.headers.get("X-Hunar-Signature"),
        body,
    )
    try:
        payload: dict[str, Any] = json.loads(body or b"{}")
    except json.JSONDecodeError:
        payload = {"raw": body.decode(errors="replace")[:2000]}

    await c.db.webhook_events.insert_one(
        {
            "_id": new_id(),
            "event_type": payload.get("event_type"),
            "hunar_call_id": payload.get("call_id"),
            "signature_valid": sig_ok,
            "received_at": utcnow(),
            "payload": payload,
        }
    )
    # A configured API key means real webhooks are possible, so the signature is the only
    # thing that makes a request trustworthy, in every environment. Trusting dev by
    # environment was safe on localhost and stops being safe the moment the backend is
    # tunnelled, which is exactly when webhooks start working. With no key the fake client
    # is in use and there is no secret to verify against, so unsigned posts are accepted.
    # Either way we answer 200, so Hunar stops retrying a request we have decided about.
    trusted = sig_ok or not c.settings.hunar_api_key
    matched: str | None = None
    if trusted:
        matched = await calls.apply_webhook(c.db, c.llm, payload)
    else:
        log.warning(
            "webhook_rejected", reason="bad_signature", event_type=payload.get("event_type")
        )
    return WebhookAck(received=True, matched=matched is not None, signature_valid=sig_ok)

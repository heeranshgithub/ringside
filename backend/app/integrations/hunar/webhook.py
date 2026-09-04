"""Webhook signature verification. Secret is the org API key (per Hunar docs)."""

from __future__ import annotations

import base64
import hashlib
import hmac


def compute_signature(secret: str, timestamp: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def verify_signature(
    secret: str, timestamp: str | None, signature_header: str | None, body: bytes
) -> bool:
    if not secret or not timestamp or not signature_header:
        return False
    expected = compute_signature(secret, timestamp, body)
    candidates = [s.strip() for s in signature_header.split(",") if s.strip()]
    return any(hmac.compare_digest(expected, c) for c in candidates)

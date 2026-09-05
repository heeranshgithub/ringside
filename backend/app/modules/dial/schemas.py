from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.core.models import ApiModel, StrictApiModel


class DialTargetDto(ApiModel):
    """What the browser is allowed to know about its own dial target."""

    id: str | None = None
    phone_masked: str
    phone_pretty: str | None = None
    verified: bool
    expires_at: datetime | None = None
    attempts_left: int | None = None


class DialCapabilityDto(ApiModel):
    """Whether this deployment will let a visitor nominate their own number, and why not."""

    enabled: bool
    reason: str | None = None
    verify_calls_left_today: int | None = None


class StartVerificationRequest(StrictApiModel):
    phone: str = Field(min_length=6, max_length=24)
    consent: bool = Field(
        description="The visitor confirms the number is theirs and accepts an automated call."
    )


class ConfirmVerificationRequest(StrictApiModel):
    code: str = Field(min_length=4, max_length=8)

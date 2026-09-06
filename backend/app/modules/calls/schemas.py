from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import Field, ValidationInfo, field_validator, model_validator

from app.core.models import ApiModel, MongoModel, StrictApiModel
from app.integrations.hunar.schemas import EARLIEST_CALL_TIME, LATEST_CALL_TIME


class CallEventDto(ApiModel):
    at: datetime
    kind: str
    status: str | None = None
    source: str = "sync"
    note: str | None = None


class TranscriptDto(ApiModel):
    language: str = ""
    turns: list[dict[str, str]] = Field(default_factory=list)
    text: str = ""


class AssessmentDto(ApiModel):
    fit_score: int
    recommendation: str
    headline: str
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    next_step: str = ""


class CallDto(MongoModel):
    hunar_call_id: str
    request_id: str | None = None
    job_id: str
    candidate_id: str
    agent_id: str
    hunar_agent_id: str
    callee_name: str
    target_number: str | None = None
    dialed_number: str
    safe_dial: bool
    dial_source: str = "env"
    custom_data: dict[str, str] = Field(default_factory=dict)
    status: str
    lifecycle_status: str
    engagement_status: str | None = None
    answered_by: str | None = None
    call_ended_by: str | None = None
    duration_seconds: float | None = None
    user_speech_duration: float | None = None
    recording_url: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    transcript: TranscriptDto | None = None
    assessment: AssessmentDto | None = None
    retry_count: int | None = None
    retries_left: int | None = None
    next_retry_scheduled_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    last_synced_at: datetime | None = None
    events: list[CallEventDto] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class GuardrailsInput(ApiModel):
    """The calling window, validated against Hunar's own limits before we send it.

    Hunar rejects a window outside 08:00-21:00 with a 400 that surfaces as a bare
    "Minimum allowed earliest_call_time is 08:00" toast. Catching it here turns that into
    our own 422 naming the field, and stops a request going out that cannot succeed.
    """

    allowed_days: list[str] = Field(
        default_factory=lambda: ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    )
    earliest_call_time: str = EARLIEST_CALL_TIME
    last_call_time: str = LATEST_CALL_TIME

    @field_validator("earliest_call_time", "last_call_time")
    @classmethod
    def _within_the_platform_window(cls, value: str, info: ValidationInfo) -> str:
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError(f"{info.field_name} must be HH:MM, got {value!r}")
        if value < EARLIEST_CALL_TIME or value > LATEST_CALL_TIME:
            raise ValueError(
                f"{info.field_name} must be between {EARLIEST_CALL_TIME} and "
                f"{LATEST_CALL_TIME}; Hunar rejects anything outside that window"
            )
        return value

    @model_validator(mode="after")
    def _ordered(self) -> GuardrailsInput:
        if self.earliest_call_time >= self.last_call_time:
            raise ValueError("earliestCallTime must be before lastCallTime")
        return self


class RetryInput(ApiModel):
    max_retry_count: int = Field(default=1, ge=0, le=10)
    retry_interval_hours: int = 3


class LaunchCallsRequest(StrictApiModel):
    job_id: str
    candidate_ids: list[str] = Field(min_length=1, max_length=200)
    agent_id: str | None = None
    guardrails: GuardrailsInput = Field(default_factory=GuardrailsInput)
    retry: RetryInput = Field(default_factory=RetryInput)


class SkippedCandidateDto(ApiModel):
    candidate_id: str
    reason: str


class LaunchCallsResponse(ApiModel):
    calls: list[CallDto]
    skipped: list[SkippedCandidateDto]


class SyncAllResponse(ApiModel):
    synced: int
    errors: int

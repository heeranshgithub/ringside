from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.models import ApiModel, MongoModel, StrictApiModel


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
    llm_used: bool = False


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
    allowed_days: list[str] = Field(
        default_factory=lambda: ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    )
    earliest_call_time: str = "00:00"
    last_call_time: str = "23:59"


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

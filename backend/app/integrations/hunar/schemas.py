"""Typed views of the Hunar Voice Agents external API (snake_case, as the upstream wire is)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

VoicePersona = Literal["NEHA", "ROY", "ZOE", "SAM", "MIRA", "EESHA"]
Language = Literal[
    "ENGLISH",
    "HINDI",
    "TAMIL",
    "TELUGU",
    "KANNADA",
    "MARATHI",
    "MALAYALAM",
    "GUJARATI",
    "BENGALI",
    "TURKISH",
    "ARABIC",
    "SPANISH",
]
CallStatus = Literal[
    "NOT_STARTED",
    "SCHEDULED",
    "INITIATED",
    "RINGING",
    "IN_PROGRESS",
    "COMPLETED",
    "NOT_CONNECTED",
    "CANCELLED",
    "FAILED",
]
LifecycleStatus = Literal[
    "NOT_STARTED", "IN_PROGRESS", "NOT_CONNECTED", "COMPLETED", "FAILED", "CANCELLED"
]

VOICE_PERSONAS: tuple[str, ...] = ("NEHA", "ROY", "ZOE", "SAM", "MIRA", "EESHA")
LANGUAGES: tuple[str, ...] = (
    "ENGLISH",
    "HINDI",
    "TAMIL",
    "TELUGU",
    "KANNADA",
    "MARATHI",
    "MALAYALAM",
    "GUJARATI",
    "BENGALI",
    "TURKISH",
    "ARABIC",
    "SPANISH",
)
TERMINAL_LIFECYCLE: frozenset[str] = frozenset(
    {"COMPLETED", "FAILED", "CANCELLED", "NOT_CONNECTED"}
)


class _Upstream(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class HunarAgentCreate(_Upstream):
    name: str = Field(min_length=3, max_length=64)
    language: str = "ENGLISH"
    voice_persona: str
    persona_name: str | None = None
    agent_prompt: str
    objective: str
    introduction: str
    result_prompt: str
    result_schema: dict[str, Any]


class HunarAgentUpdate(_Upstream):
    name: str | None = None
    language: str | None = None
    voice_persona: str | None = None
    persona_name: str | None = None
    agent_prompt: str | None = None
    objective: str | None = None
    introduction: str | None = None
    result_prompt: str | None = None
    result_schema: dict[str, Any] | None = None


class HunarAgent(_Upstream):
    id: str
    status: str = "ACTIVE"
    name: str
    voice_persona: str
    persona_name: str | None = None
    voice_name: str | None = None
    summary: str | None = None
    logo: str | None = None
    language: str = "ENGLISH"
    custom_variables: list[str] = Field(default_factory=list)
    required_variables: list[str] = Field(default_factory=list)
    result_schema: dict[str, Any] = Field(default_factory=dict)
    agent_code: str | None = None
    created_at: str | None = None
    agent_prompt: str | None = None
    introduction: str | None = None
    objective: str | None = None
    result_prompt: str | None = None
    silence_response: str | None = None
    conclusion: str | None = None


class RetryConfig(_Upstream):
    max_retry_count: int = Field(ge=0, le=10)
    retry_interval_hours: int


# Hunar enforces a calling window server-side and rejects anything outside it with a 400,
# before it even looks up the agent. The bounds are not in their OpenAPI schema; these were
# measured against the live API on 2026-09-06.
EARLIEST_CALL_TIME = "08:00"
LATEST_CALL_TIME = "21:00"


class Guardrails(_Upstream):
    allowed_days: list[str]
    earliest_call_time: str
    last_call_time: str


class CallbackConfig(_Upstream):
    call_status_callback_url: str | None = None
    call_recording_callback_url: str | None = None
    call_result_callback_url: str | None = None
    call_summary_callback_url: str | None = None


class HunarCallCreate(_Upstream):
    agent_id: str
    callee_name: str
    mobile_number: str
    custom_data: dict[str, str] = Field(default_factory=dict)
    request_id: str | None = None
    from_phone_number: str | None = None
    timezone: str | None = None
    retry_config: RetryConfig | None = None
    guardrails: Guardrails | None = None
    callback_config: CallbackConfig | None = None


class HunarRecipient(_Upstream):
    callee_name: str
    mobile_number: str
    custom_data: dict[str, str] = Field(default_factory=dict)


class HunarBulkCallCreate(_Upstream):
    agent_id: str
    data: list[HunarRecipient]
    request_id: str | None = None
    from_phone_number: str | None = None
    timezone: str | None = None
    retry_config: RetryConfig | None = None
    guardrails: Guardrails | None = None
    callback_config: CallbackConfig | None = None
    remove_invalid_rows: bool = True
    remove_duplicate_phone_numbers: bool = True


class HunarCallCreated(_Upstream):
    id: str
    request_id: str | None = None
    status: str
    callee_name: str
    mobile_number: str
    timezone: str | None = None
    from_phone_number: str | None = None


class HunarCall(_Upstream):
    id: str
    callee_name: str
    mobile_number: str
    agent_id: str
    language: str | None = None
    campaign_id: str | None = None
    call_type: str | None = None
    status: str
    lifecycle_status: str
    custom_data: dict[str, Any] = Field(default_factory=dict)
    system_data: dict[str, Any] = Field(default_factory=dict)
    duration_minutes: float | None = None
    duration_seconds: float | None = None
    user_speech_duration: float | None = None
    engagement_status: str | None = None
    answered_by: str | None = None
    call_ended_by: str | None = None
    recording_url: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    max_retries: int | None = None
    retry_count: int | None = None
    retries_left: int | None = None
    next_retry_scheduled_at: str | None = None
    redial_status: str | None = None
    timezone: str | None = None
    from_phone_number: str | None = None
    request_id: str | None = None


class Paginated(_Upstream):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[dict[str, Any]] = Field(default_factory=list)


class HunarNumber(_Upstream):
    id: str
    phone_number: str
    provider: str | None = None
    country_code: str | None = None
    is_default: bool = False
    is_validated: bool = False

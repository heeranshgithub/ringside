from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import Field

from app.core.deps import ContainerDep, DbDep
from app.core.models import ApiModel
from app.modules.calls.schemas import CallDto

router = APIRouter(tags=["dashboard"])


class DashboardSummaryDto(ApiModel):
    jobs: int
    agents: int
    candidates: int
    calls_total: int
    calls_by_status: dict[str, int] = Field(default_factory=dict)
    calls_by_lifecycle: dict[str, int] = Field(default_factory=dict)
    engaged: int
    completed: int
    pending: int
    avg_duration_seconds: float | None = None
    recommendation_counts: dict[str, int] = Field(default_factory=dict)
    recent_calls: list[CallDto] = Field(default_factory=list)


class CapabilityDto(ApiModel):
    """One integration, and whether it will actually do anything."""

    key: str
    label: str
    # ok = real credentials · degraded = a deliberate offline stand-in · missing = will refuse
    state: Literal["ok", "degraded", "missing"]
    detail: str
    env_var: str | None = None


class ConfigDto(ApiModel):
    env: str
    capabilities: list[CapabilityDto] = Field(default_factory=list)
    safe_dial_mode: bool
    hunar_enabled: bool
    llm_enabled: bool
    llm_model: str
    webhooks_enabled: bool
    poller_enabled: bool
    poller_interval_seconds: int
    providers: list[str]
    access_code_required: bool
    client_dial_enabled: bool


def _capabilities(c: ContainerDep) -> list[CapabilityDto]:
    s = c.settings
    caps = [
        CapabilityDto(
            key="hunar",
            label="Hunar voice platform",
            state="ok" if s.hunar_enabled else "missing",
            detail=(
                "Agents and calls go to the real API."
                if s.hunar_enabled
                else "Creating agents and placing calls will be refused, never simulated."
            ),
            env_var=None if s.hunar_enabled else "HUNAR_API_KEY",
        ),
        CapabilityDto(
            key="llm",
            label="Language model",
            state="ok" if c.llm.enabled else "missing",
            detail=(
                f"Parsing, drafting and scoring use {s.llm_model}."
                if c.llm.enabled
                else "Job parsing, agent drafting, scoring and transcription are refused."
            ),
            env_var=None if c.llm.enabled else "OPENROUTER_API_KEY",
        ),
        CapabilityDto(
            key="dialling",
            label="Safe dial target",
            # Reports whether the mechanism is available, not whether this visitor has used it:
            # the target is per browser and this response is not.
            state="ok" if s.client_dial_enabled else "missing",
            detail=(
                "Each visitor verifies their own number, and that is the only phone we ring."
                if s.client_dial_enabled
                else (
                    s.client_dial_blocked_reason
                    or "Nobody can nominate a number, so every call launch will be refused."
                )
            ),
            env_var=(
                None
                if s.client_dial_enabled
                else "APP_ACCESS_CODE"
                if s.allow_client_dial_target
                else "ALLOW_CLIENT_DIAL_TARGET"
            ),
        ),
        CapabilityDto(
            key="people_search",
            label="People search",
            state="ok" if len(c.providers) > 1 else "degraded",
            detail=(
                f"Live providers: {', '.join(sorted(k for k in c.providers if k != 'mock'))}."
                if len(c.providers) > 1
                else "Only the seeded demo dataset. No third-party source is configured."
            ),
            env_var=None if len(c.providers) > 1 else "PDL_API_KEY",
        ),
        CapabilityDto(
            key="webhooks",
            label="Call webhooks",
            state="ok" if s.webhooks_enabled else "degraded",
            detail=(
                "Hunar pushes call updates directly to this backend."
                if s.webhooks_enabled
                else "No public URL, so updates arrive only from the background poller."
            ),
            env_var=None if s.webhooks_enabled else "PUBLIC_BASE_URL",
        ),
    ]
    return caps


@router.get("/config", response_model=ConfigDto)
async def config(c: ContainerDep) -> ConfigDto:
    s = c.settings
    return ConfigDto(
        env=s.env,
        safe_dial_mode=s.safe_dial_mode,
        hunar_enabled=s.hunar_enabled,
        llm_enabled=c.llm.enabled,
        llm_model=s.llm_model if c.llm.enabled else "not configured",
        capabilities=_capabilities(c),
        webhooks_enabled=s.webhooks_enabled,
        poller_enabled=s.poller_enabled,
        poller_interval_seconds=s.poller_interval_seconds,
        providers=sorted(c.providers.keys()),
        access_code_required=bool(s.app_access_code),
        client_dial_enabled=s.client_dial_enabled,
    )


@router.get("/dashboard/summary", response_model=DashboardSummaryDto)
async def summary(db: DbDep) -> DashboardSummaryDto:
    raw = await db.calls.find().sort("created_at", -1).to_list(length=2000)
    calls: list[dict[str, Any]] = [dict(c) for c in raw]
    by_status: dict[str, int] = {}
    by_lifecycle: dict[str, int] = {}
    recs: dict[str, int] = {}
    durations: list[float] = []
    engaged = completed = pending = 0
    for c in calls:
        by_status[c.get("status", "?")] = by_status.get(c.get("status", "?"), 0) + 1
        lc = c.get("lifecycle_status", "?")
        by_lifecycle[lc] = by_lifecycle.get(lc, 0) + 1
        if c.get("engagement_status") == "ENGAGED":
            engaged += 1
        if lc == "COMPLETED":
            completed += 1
            if c.get("duration_seconds"):
                durations.append(float(c["duration_seconds"]))
        elif lc in ("NOT_STARTED", "IN_PROGRESS"):
            pending += 1
        rec = (c.get("assessment") or {}).get("recommendation")
        if rec:
            recs[rec] = recs.get(rec, 0) + 1
    return DashboardSummaryDto(
        jobs=await db.jobs.count_documents({}),
        agents=await db.agents.count_documents({}),
        candidates=await db.candidates.count_documents({}),
        calls_total=len(calls),
        calls_by_status=by_status,
        calls_by_lifecycle=by_lifecycle,
        engaged=engaged,
        completed=completed,
        pending=pending,
        avg_duration_seconds=round(sum(durations) / len(durations), 1) if durations else None,
        recommendation_counts=recs,
        recent_calls=[CallDto.model_validate(c) for c in calls[:8]],
    )

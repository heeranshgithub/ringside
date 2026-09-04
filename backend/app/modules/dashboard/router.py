from __future__ import annotations

from typing import Any

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


class ConfigDto(ApiModel):
    env: str
    safe_dial_mode: bool
    test_phone_numbers_masked: list[str]
    hunar_enabled: bool
    llm_enabled: bool
    llm_model: str
    webhooks_enabled: bool
    poller_enabled: bool
    poller_interval_seconds: int
    providers: list[str]
    access_code_required: bool


def _mask(phone: str) -> str:
    return phone[:3] + "•" * max(0, len(phone) - 6) + phone[-3:] if len(phone) > 6 else "•••"


@router.get("/config", response_model=ConfigDto)
async def config(c: ContainerDep) -> ConfigDto:
    s = c.settings
    return ConfigDto(
        env=s.env,
        safe_dial_mode=s.safe_dial_mode,
        test_phone_numbers_masked=[_mask(p) for p in s.test_phone_numbers],
        hunar_enabled=s.hunar_enabled,
        llm_enabled=c.llm.enabled,
        llm_model=s.llm_model if c.llm.enabled else "rule-based fallback",
        webhooks_enabled=s.webhooks_enabled,
        poller_enabled=s.poller_enabled,
        poller_interval_seconds=s.poller_interval_seconds,
        providers=sorted(c.providers.keys()),
        access_code_required=bool(s.app_access_code),
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

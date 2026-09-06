from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.deps import DbDep, EventsDep, HunarDep, LlmDep, SessionId, SettingsDep
from app.core.pagination import Page
from app.modules.calls import service
from app.modules.calls.schemas import (
    CallDto,
    LaunchCallsRequest,
    LaunchCallsResponse,
    SyncAllResponse,
)
from app.modules.dial import service as dial_service

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("", response_model=Page[CallDto])
async def list_calls(
    db: DbDep,
    job_id: str | None = Query(None, alias="jobId"),
    candidate_id: str | None = Query(None, alias="candidateId"),
    statuses: Annotated[list[str] | None, Query(alias="status")] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200, alias="pageSize"),
) -> Page[CallDto]:
    return await service.list_calls(
        db,
        job_id=job_id,
        candidate_id=candidate_id,
        statuses=statuses,
        page=page,
        page_size=page_size,
    )


@router.post("/launch", response_model=LaunchCallsResponse, status_code=status.HTTP_201_CREATED)
async def launch(
    body: LaunchCallsRequest,
    db: DbDep,
    hunar: HunarDep,
    settings: SettingsDep,
    x_session_id: SessionId = None,
) -> LaunchCallsResponse:
    # Safe dial has no server-side number behind it, so the destination is whatever this
    # browser proved is its own. Without this lookup the whole verification flow would be
    # decorative: every launch would refuse.
    target = await dial_service.current_target(db, x_session_id) if x_session_id else None
    return await service.launch_calls(
        db, hunar, settings, body, verified_target=target["phone"] if target else None
    )


@router.post("/sync", response_model=SyncAllResponse)
async def sync_all(db: DbDep, hunar: HunarDep, llm: LlmDep, events: EventsDep) -> SyncAllResponse:
    synced, errors = await service.sync_pending(db, hunar, llm, limit=100, bus=events)
    return SyncAllResponse(synced=synced, errors=errors)


@router.get("/{id}", response_model=CallDto)
async def get_call(id: str, db: DbDep) -> CallDto:
    return await service.get_call(db, id)


@router.post("/{id}/sync", response_model=CallDto)
async def sync_one(id: str, db: DbDep, hunar: HunarDep, llm: LlmDep, events: EventsDep) -> CallDto:
    return await service.sync_call(db, hunar, llm, id, source="manual", bus=events)


@router.post("/{id}/assess", response_model=CallDto)
async def assess(id: str, db: DbDep, llm: LlmDep) -> CallDto:
    return await service.assess_call(db, llm, id)


@router.post("/{id}/transcribe", response_model=CallDto)
async def transcribe(id: str, db: DbDep, llm: LlmDep) -> CallDto:
    return await service.transcribe_call(db, llm, id)

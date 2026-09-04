from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.deps import DbDep, HunarDep, LlmDep, SettingsDep
from app.core.pagination import Page
from app.modules.calls import service
from app.modules.calls.schemas import (
    CallDto,
    LaunchCallsRequest,
    LaunchCallsResponse,
    SyncAllResponse,
)

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
    body: LaunchCallsRequest, db: DbDep, hunar: HunarDep, settings: SettingsDep
) -> LaunchCallsResponse:
    return await service.launch_calls(db, hunar, settings, body)


@router.post("/sync", response_model=SyncAllResponse)
async def sync_all(db: DbDep, hunar: HunarDep, llm: LlmDep) -> SyncAllResponse:
    synced, errors = await service.sync_pending(db, hunar, llm, limit=100)
    return SyncAllResponse(synced=synced, errors=errors)


@router.get("/{id}", response_model=CallDto)
async def get_call(id: str, db: DbDep) -> CallDto:
    return await service.get_call(db, id)


@router.post("/{id}/sync", response_model=CallDto)
async def sync_one(id: str, db: DbDep, hunar: HunarDep, llm: LlmDep) -> CallDto:
    return await service.sync_call(db, hunar, llm, id, source="manual")


@router.post("/{id}/assess", response_model=CallDto)
async def assess(id: str, db: DbDep, llm: LlmDep) -> CallDto:
    return await service.assess_call(db, llm, id)


@router.post("/{id}/transcribe", response_model=CallDto)
async def transcribe(id: str, db: DbDep, llm: LlmDep) -> CallDto:
    return await service.transcribe_call(db, llm, id)

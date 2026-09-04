from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import DbDep, LlmDep
from app.modules.jobs import service
from app.modules.jobs.schemas import (
    CreateJobRequest,
    JobDto,
    ParsedJobDto,
    ParseJobRequest,
    UpdateJobRequest,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/parse", response_model=ParsedJobDto)
async def parse_job(body: ParseJobRequest, llm: LlmDep) -> ParsedJobDto:
    return await service.parse_description(llm, body.description)


@router.get("", response_model=list[JobDto])
async def list_jobs(db: DbDep) -> list[JobDto]:
    return await service.list_jobs(db)


@router.post("", response_model=JobDto, status_code=status.HTTP_201_CREATED)
async def create_job(body: CreateJobRequest, db: DbDep) -> JobDto:
    return await service.create_job(db, body)


@router.get("/{id}", response_model=JobDto)
async def get_job(id: str, db: DbDep) -> JobDto:
    return await service.get_job(db, id)


@router.patch("/{id}", response_model=JobDto)
async def update_job(id: str, body: UpdateJobRequest, db: DbDep) -> JobDto:
    return await service.update_job(db, id, body)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(id: str, db: DbDep) -> None:
    await service.delete_job(db, id)

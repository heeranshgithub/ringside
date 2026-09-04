from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.deps import DbDep
from app.modules.candidates import service
from app.modules.candidates.schemas import (
    CandidateDto,
    CreateCandidateRequest,
    ImportCsvRequest,
    ImportCsvResponse,
    UpdateCandidateRequest,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=list[CandidateDto])
async def list_candidates(
    db: DbDep, job_id: str | None = Query(None, alias="jobId")
) -> list[CandidateDto]:
    return await service.list_candidates(db, job_id)


@router.post("", response_model=CandidateDto, status_code=status.HTTP_201_CREATED)
async def create_candidate(body: CreateCandidateRequest, db: DbDep) -> CandidateDto:
    return await service.create_candidate(db, body)


@router.post("/import-csv", response_model=ImportCsvResponse, status_code=status.HTTP_201_CREATED)
async def import_csv(body: ImportCsvRequest, db: DbDep) -> ImportCsvResponse:
    return await service.import_csv(db, body.job_id, body.csv_text)


@router.patch("/{id}", response_model=CandidateDto)
async def update_candidate(id: str, body: UpdateCandidateRequest, db: DbDep) -> CandidateDto:
    return await service.update_candidate(db, id, body)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(id: str, db: DbDep) -> None:
    await service.delete_candidate(db, id)

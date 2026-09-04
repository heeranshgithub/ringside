from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.db import Db, as_doc
from app.core.errors import JobNotFound
from app.core.models import new_id, utcnow
from app.integrations.llm.client import LlmService
from app.modules.jobs.schemas import (
    CreateJobRequest,
    JobDto,
    ParsedJobDto,
    UpdateJobRequest,
)


async def parse_description(llm: LlmService, description: str) -> ParsedJobDto:
    parsed = await llm.parse_job(description)
    return ParsedJobDto.model_validate({**parsed.model_dump(), "llm_used": llm.enabled})


async def _with_counts(db: Db, raw: Mapping[str, Any]) -> JobDto:
    doc = as_doc(raw)
    doc["candidate_count"] = await db.candidates.count_documents({"job_id": doc["_id"]})
    doc["call_count"] = await db.calls.count_documents({"job_id": doc["_id"]})
    return JobDto.model_validate(doc)


async def create_job(db: Db, body: CreateJobRequest) -> JobDto:
    now = utcnow()
    doc: dict[str, Any] = {
        "_id": new_id(),
        **body.model_dump(),
        "agent_id": None,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }
    await db.jobs.insert_one(doc)
    return await _with_counts(db, doc)


async def list_jobs(db: Db) -> list[JobDto]:
    docs = await db.jobs.find().sort("created_at", -1).to_list(length=200)
    return [await _with_counts(db, d) for d in docs]


async def get_job_doc(db: Db, job_id: str) -> dict[str, Any]:
    doc = await db.jobs.find_one({"_id": job_id})
    if not doc:
        raise JobNotFound(f"Job {job_id} not found")
    return as_doc(doc)


async def get_job(db: Db, job_id: str) -> JobDto:
    return await _with_counts(db, await get_job_doc(db, job_id))


async def update_job(db: Db, job_id: str, body: UpdateJobRequest) -> JobDto:
    await get_job_doc(db, job_id)
    updates = body.model_dump(exclude_unset=True)
    updates["updated_at"] = utcnow()
    await db.jobs.update_one({"_id": job_id}, {"$set": updates})
    return await get_job(db, job_id)


async def delete_job(db: Db, job_id: str) -> None:
    await get_job_doc(db, job_id)
    await db.jobs.delete_one({"_id": job_id})
    await db.candidates.delete_many({"job_id": job_id})
    await db.calls.delete_many({"job_id": job_id})


def job_for_llm(doc: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "title",
        "company",
        "location",
        "employment_type",
        "seniority",
        "salary_range",
        "summary",
        "must_haves",
        "nice_to_haves",
        "screening_questions",
    )
    return {k: doc.get(k) for k in keys}

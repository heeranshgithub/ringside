from __future__ import annotations

import csv
import io
import re
from typing import Any

from app.core.db import Db, as_doc
from app.core.errors import CandidateNotFound, ValidationFailed
from app.core.models import new_id, utcnow
from app.core.phone import normalize_phone
from app.integrations.people.base import PersonResult
from app.modules.candidates.schemas import (
    CandidateDto,
    CreateCandidateRequest,
    ImportCsvResponse,
    UpdateCandidateRequest,
)
from app.modules.jobs.service import get_job_doc


def _doc_from_request(body: CreateCandidateRequest) -> dict[str, Any]:
    now = utcnow()
    return {
        "_id": new_id(),
        **body.model_dump(),
        "phone": normalize_phone(body.phone),
        "source": "manual",
        "source_ref": None,
        "linkedin_url": None,
        "latest_call_id": None,
        "latest_call_status": None,
        "created_at": now,
        "updated_at": now,
    }


async def create_candidate(db: Db, body: CreateCandidateRequest) -> CandidateDto:
    await get_job_doc(db, body.job_id)
    doc = _doc_from_request(body)
    await db.candidates.insert_one(doc)
    return CandidateDto.model_validate(doc)


async def import_csv(db: Db, job_id: str, csv_text: str) -> ImportCsvResponse:
    await get_job_doc(db, job_id)
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if not reader.fieldnames:
        raise ValidationFailed("CSV has no header row")
    headers = {h.strip().lower().replace(" ", "_"): h for h in reader.fieldnames if h}
    if "name" not in headers:
        raise ValidationFailed(
            "CSV needs at least a 'name' column "
            "(optional: phone, email, title, company, location, skills)"
        )

    def col(row: dict[str, Any], *names: str) -> str | None:
        for n in names:
            if n in headers and row.get(headers[n]):
                return str(row[headers[n]]).strip()
        return None

    created: list[CandidateDto] = []
    skipped: list[str] = []
    now = utcnow()
    for i, row in enumerate(reader, start=2):
        name = col(row, "name", "full_name", "candidate_name")
        if not name:
            skipped.append(f"row {i}: missing name")
            continue
        try:
            phone = normalize_phone(col(row, "phone", "mobile", "mobile_number", "phone_number"))
        except ValidationFailed as exc:
            skipped.append(f"row {i}: {exc.message}")
            continue
        skills_raw = col(row, "skills") or ""
        doc = {
            "_id": new_id(),
            "job_id": job_id,
            "name": name,
            "phone": phone,
            "email": col(row, "email"),
            "current_title": col(row, "title", "current_title", "job_title"),
            "current_company": col(row, "company", "current_company"),
            "location": col(row, "location", "city"),
            "skills": [s.strip() for s in re.split(r"[;|,]", skills_raw) if s.strip()],
            "summary": col(row, "summary", "notes"),
            "years_experience": None,
            "source": "csv",
            "source_ref": None,
            "linkedin_url": col(row, "linkedin", "linkedin_url"),
            "allow_real_dial": False,
            "latest_call_id": None,
            "latest_call_status": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.candidates.insert_one(doc)
        created.append(CandidateDto.model_validate(doc))
    return ImportCsvResponse(created=created, skipped=skipped)


async def import_people(db: Db, job_id: str, people: list[PersonResult]) -> list[CandidateDto]:
    await get_job_doc(db, job_id)
    out: list[CandidateDto] = []
    now = utcnow()
    for p in people:
        existing = await db.candidates.find_one(
            {"job_id": job_id, "source": p.source, "source_ref": p.source_ref}
        )
        if existing:
            out.append(CandidateDto.model_validate(existing))
            continue
        phone: str | None = None
        if p.phone:
            try:
                phone = normalize_phone(p.phone)
            except ValidationFailed:
                phone = None
        doc = {
            "_id": new_id(),
            "job_id": job_id,
            "name": p.name,
            "phone": phone,
            "email": p.email,
            "current_title": p.current_title,
            "current_company": p.current_company,
            "location": p.location,
            "skills": p.skills,
            "summary": p.summary,
            "years_experience": p.years_experience,
            "source": p.source,
            "source_ref": p.source_ref,
            "linkedin_url": p.linkedin_url,
            "allow_real_dial": False,
            "latest_call_id": None,
            "latest_call_status": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.candidates.insert_one(doc)
        out.append(CandidateDto.model_validate(doc))
    return out


async def list_candidates(db: Db, job_id: str | None) -> list[CandidateDto]:
    q: dict[str, Any] = {"job_id": job_id} if job_id else {}
    docs = await db.candidates.find(q).sort("created_at", -1).to_list(length=1000)
    return [CandidateDto.model_validate(d) for d in docs]


async def get_candidate_doc(db: Db, candidate_id: str) -> dict[str, Any]:
    doc = await db.candidates.find_one({"_id": candidate_id})
    if not doc:
        raise CandidateNotFound(f"Candidate {candidate_id} not found")
    return as_doc(doc)


async def update_candidate(db: Db, candidate_id: str, body: UpdateCandidateRequest) -> CandidateDto:
    await get_candidate_doc(db, candidate_id)
    changes = body.model_dump(exclude_unset=True)
    if "phone" in changes:
        changes["phone"] = normalize_phone(changes["phone"])
    changes["updated_at"] = utcnow()
    await db.candidates.update_one({"_id": candidate_id}, {"$set": changes})
    return CandidateDto.model_validate(await get_candidate_doc(db, candidate_id))


async def delete_candidate(db: Db, candidate_id: str) -> None:
    await get_candidate_doc(db, candidate_id)
    await db.candidates.delete_one({"_id": candidate_id})

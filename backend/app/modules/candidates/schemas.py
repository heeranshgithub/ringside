from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.core.models import ApiModel, MongoModel, StrictApiModel


class CandidateDto(MongoModel):
    job_id: str
    name: str
    phone: str | None = None
    email: str | None = None
    current_title: str | None = None
    current_company: str | None = None
    location: str | None = None
    skills: list[str] = Field(default_factory=list)
    source: str = "manual"
    source_ref: str | None = None
    linkedin_url: str | None = None
    summary: str | None = None
    years_experience: float | None = None
    allow_real_dial: bool = False
    latest_call_id: str | None = None
    latest_call_status: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateCandidateRequest(StrictApiModel):
    job_id: str
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=200)
    current_title: str | None = None
    current_company: str | None = None
    location: str | None = None
    skills: list[str] = Field(default_factory=list)
    summary: str | None = None
    years_experience: float | None = None
    allow_real_dial: bool = False


class UpdateCandidateRequest(StrictApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = None
    email: str | None = None
    current_title: str | None = None
    current_company: str | None = None
    location: str | None = None
    skills: list[str] | None = None
    summary: str | None = None
    years_experience: float | None = None
    allow_real_dial: bool | None = None


class ImportCsvRequest(StrictApiModel):
    job_id: str
    csv_text: str = Field(min_length=1, max_length=500_000)


class ImportCsvResponse(ApiModel):
    created: list[CandidateDto]
    skipped: list[str]

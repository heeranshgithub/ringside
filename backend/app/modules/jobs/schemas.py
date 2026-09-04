from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.core.models import ApiModel, MongoModel, StrictApiModel

JobStatus = Literal["draft", "active", "closed"]


class SearchCriteriaDto(ApiModel):
    titles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    seniorities: list[str] = Field(default_factory=list)
    keywords: str = ""


class JobDto(MongoModel):
    title: str
    company: str | None = None
    location: str | None = None
    description: str
    employment_type: str | None = None
    seniority: str | None = None
    salary_range: str | None = None
    summary: str = ""
    must_haves: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    screening_questions: list[str] = Field(default_factory=list)
    search_criteria: SearchCriteriaDto = Field(default_factory=SearchCriteriaDto)
    agent_id: str | None = None
    status: JobStatus = "draft"
    candidate_count: int = 0
    call_count: int = 0
    created_at: datetime
    updated_at: datetime


class ParsedJobDto(ApiModel):
    title: str
    company: str | None = None
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    salary_range: str | None = None
    summary: str = ""
    must_haves: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    screening_questions: list[str] = Field(default_factory=list)
    search_criteria: SearchCriteriaDto = Field(default_factory=SearchCriteriaDto)
    llm_used: bool = False


class ParseJobRequest(StrictApiModel):
    description: str = Field(min_length=20, max_length=20000)


class CreateJobRequest(StrictApiModel):
    title: str = Field(min_length=2, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    description: str = Field(min_length=20, max_length=20000)
    employment_type: str | None = None
    seniority: str | None = None
    salary_range: str | None = None
    summary: str = ""
    must_haves: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    screening_questions: list[str] = Field(default_factory=list)
    search_criteria: SearchCriteriaDto = Field(default_factory=SearchCriteriaDto)


class UpdateJobRequest(StrictApiModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    company: str | None = None
    location: str | None = None
    description: str | None = Field(default=None, min_length=20, max_length=20000)
    employment_type: str | None = None
    seniority: str | None = None
    salary_range: str | None = None
    summary: str | None = None
    must_haves: list[str] | None = None
    nice_to_haves: list[str] | None = None
    screening_questions: list[str] | None = None
    search_criteria: SearchCriteriaDto | None = None
    agent_id: str | None = None
    status: JobStatus | None = None

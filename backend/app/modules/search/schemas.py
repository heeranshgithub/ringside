from __future__ import annotations

from pydantic import Field

from app.core.models import ApiModel, StrictApiModel


class PersonDto(ApiModel):
    source: str
    source_ref: str
    name: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    current_title: str | None = None
    current_company: str | None = None
    location: str | None = None
    skills: list[str] = Field(default_factory=list)
    linkedin_url: str | None = None
    summary: str | None = None
    years_experience: float | None = None


class SearchCriteriaInput(ApiModel):
    titles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    seniorities: list[str] = Field(default_factory=list)
    keywords: str = ""
    limit: int = Field(default=10, ge=1, le=50)


class SearchPeopleRequest(StrictApiModel):
    provider: str = "mock"
    criteria: SearchCriteriaInput


class SearchPeopleResponse(ApiModel):
    provider: str
    results: list[PersonDto]


class ImportPeopleRequest(StrictApiModel):
    job_id: str
    people: list[PersonDto] = Field(min_length=1, max_length=100)


class ProviderInfoDto(ApiModel):
    name: str
    configured: bool
    label: str
    note: str
    # When set, the server clamps a search to this many records and the picker follows.
    max_results: int | None = None

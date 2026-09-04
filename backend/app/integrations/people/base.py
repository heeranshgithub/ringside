"""People-search provider abstraction. One Protocol, several backends, one normalized person."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field

ProviderName = Literal["mock", "apollo", "pdl"]


class SearchCriteria(BaseModel):
    titles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    seniorities: list[str] = Field(default_factory=list)
    keywords: str = ""
    limit: int = Field(default=10, ge=1, le=50)


class PersonResult(BaseModel):
    """Normalized shape across providers (snake_case, internal)."""

    source: ProviderName
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


class PeopleProvider(Protocol):
    name: str

    async def search(self, criteria: SearchCriteria) -> list[PersonResult]: ...

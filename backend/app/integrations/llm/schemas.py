"""Structured outputs we ask the LLM for. Internal snake_case; converted at the API boundary."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParsedSearchCriteria(BaseModel):
    titles: list[str] = Field(default_factory=list, description="3-6 job titles to search for")
    locations: list[str] = Field(
        default_factory=list, description="cities/regions, e.g. 'Bengaluru'"
    )
    skills: list[str] = Field(default_factory=list, description="lowercase skill keywords")
    seniorities: list[str] = Field(
        default_factory=list, description="entry|senior|manager|director|vp"
    )
    keywords: str = ""


class ParsedJob(BaseModel):
    title: str
    company: str | None = None
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    salary_range: str | None = None
    summary: str = ""
    must_haves: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    screening_questions: list[str] = Field(
        default_factory=list, description="5-8 short questions a phone screener should ask"
    )
    search_criteria: ParsedSearchCriteria = Field(default_factory=ParsedSearchCriteria)


class AgentDraft(BaseModel):
    name: str = Field(max_length=64)
    persona_name: str = "Neha"
    voice_persona: str = "NEHA"
    language: str = "ENGLISH"
    introduction: str
    objective: str
    agent_prompt: str
    result_prompt: str
    result_schema: dict[str, Any]


class CallAssessment(BaseModel):
    fit_score: int = Field(ge=0, le=100)
    recommendation: str = Field(description="strong_yes|yes|maybe|no|insufficient_data")
    headline: str = Field(description="one-line verdict")
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    next_step: str = ""


class Transcript(BaseModel):
    language: str = ""
    turns: list[dict[str, str]] = Field(
        default_factory=list, description="[{speaker: 'agent'|'candidate', text: '...'}]"
    )
    text: str = ""

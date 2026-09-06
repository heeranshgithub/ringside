from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.models import ApiModel, MongoModel, StrictApiModel


class AgentDto(MongoModel):
    hunar_agent_id: str
    agent_code: str | None = None
    name: str
    language: str
    voice_persona: str
    persona_name: str | None = None
    introduction: str
    objective: str
    agent_prompt: str
    result_prompt: str | None = None
    result_schema: dict[str, Any] = Field(default_factory=dict)
    custom_variables: list[str] = Field(default_factory=list)
    job_id: str | None = None
    status: str = "ACTIVE"
    source: str = "manual"
    created_at: datetime
    updated_at: datetime


class AgentDraftDto(ApiModel):
    name: str
    persona_name: str
    voice_persona: str
    language: str
    introduction: str
    objective: str
    agent_prompt: str
    result_prompt: str
    result_schema: dict[str, Any]


class DraftAgentRequest(StrictApiModel):
    job_id: str


class CreateAgentRequest(StrictApiModel):
    job_id: str | None = None
    name: str = Field(min_length=3, max_length=64)
    language: str = "ENGLISH"
    voice_persona: str = "NEHA"
    persona_name: str | None = Field(default=None, min_length=3, max_length=64)
    introduction: str = Field(min_length=3)
    objective: str = Field(min_length=3)
    agent_prompt: str = Field(min_length=3)
    result_prompt: str = Field(min_length=3)
    result_schema: dict[str, Any] = Field(min_length=1)
    source: str = "manual"


class UpdateAgentRequest(StrictApiModel):
    name: str | None = Field(default=None, min_length=3, max_length=64)
    language: str | None = None
    voice_persona: str | None = None
    persona_name: str | None = Field(default=None, min_length=3, max_length=64)
    introduction: str | None = Field(default=None, min_length=3)
    objective: str | None = Field(default=None, min_length=3)
    agent_prompt: str | None = Field(default=None, min_length=3)
    result_prompt: str | None = Field(default=None, min_length=3)
    result_schema: dict[str, Any] | None = None
    job_id: str | None = None


class ImportAgentRequest(StrictApiModel):
    hunar_agent_id: str
    job_id: str | None = None


class AgentOptionsDto(ApiModel):
    voice_personas: list[str]
    languages: list[str]

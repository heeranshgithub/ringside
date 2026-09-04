from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.deps import DbDep, HunarDep, LlmDep
from app.integrations.hunar.schemas import LANGUAGES, VOICE_PERSONAS
from app.modules.agents import service
from app.modules.agents.schemas import (
    AgentDraftDto,
    AgentDto,
    AgentOptionsDto,
    CreateAgentRequest,
    DraftAgentRequest,
    ImportAgentRequest,
    UpdateAgentRequest,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/options", response_model=AgentOptionsDto)
async def options() -> AgentOptionsDto:
    return AgentOptionsDto(voice_personas=list(VOICE_PERSONAS), languages=list(LANGUAGES))


@router.post("/draft", response_model=AgentDraftDto)
async def draft(body: DraftAgentRequest, db: DbDep, llm: LlmDep) -> AgentDraftDto:
    return await service.draft_agent(db, llm, body.job_id)


@router.get("", response_model=list[AgentDto])
async def list_agents(db: DbDep, job_id: str | None = Query(None, alias="jobId")) -> list[AgentDto]:
    return await service.list_agents(db, job_id)


@router.post("", response_model=AgentDto, status_code=status.HTTP_201_CREATED)
async def create_agent(body: CreateAgentRequest, db: DbDep, hunar: HunarDep) -> AgentDto:
    return await service.create_agent(db, hunar, body)


@router.post("/import", response_model=AgentDto, status_code=status.HTTP_201_CREATED)
async def import_agent(body: ImportAgentRequest, db: DbDep, hunar: HunarDep) -> AgentDto:
    return await service.import_agent(db, hunar, body.hunar_agent_id, body.job_id)


@router.get("/{id}", response_model=AgentDto)
async def get_agent(id: str, db: DbDep) -> AgentDto:
    return await service.get_agent(db, id)


@router.patch("/{id}", response_model=AgentDto)
async def update_agent(id: str, body: UpdateAgentRequest, db: DbDep, hunar: HunarDep) -> AgentDto:
    return await service.update_agent(db, hunar, id, body)


@router.post("/{id}/refresh", response_model=AgentDto)
async def refresh_agent(id: str, db: DbDep, hunar: HunarDep) -> AgentDto:
    return await service.refresh_agent(db, hunar, id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(id: str, db: DbDep) -> None:
    await service.delete_agent(db, id)

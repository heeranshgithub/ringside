from __future__ import annotations

import re
from typing import Any

from app.core.db import Db, as_doc
from app.core.errors import AgentNotFound, ValidationFailed
from app.core.models import new_id, utcnow
from app.integrations.hunar.client import HunarClient
from app.integrations.hunar.schemas import (
    LANGUAGES,
    VOICE_PERSONAS,
    HunarAgent,
    HunarAgentCreate,
    HunarAgentUpdate,
)
from app.integrations.llm.client import LlmService
from app.modules.agents.schemas import (
    AgentDraftDto,
    AgentDto,
    CreateAgentRequest,
    UpdateAgentRequest,
)
from app.modules.jobs.service import get_job_doc, job_for_llm

_VAR_RE = re.compile(r"{(\w+)}")


def extract_variables(*texts: str | None) -> list[str]:
    found: set[str] = set()
    for t in texts:
        if t:
            found.update(_VAR_RE.findall(t))
    found.discard("persona_name")
    return sorted(found)


def _validate_choices(language: str | None, voice_persona: str | None) -> None:
    if language and language not in LANGUAGES:
        raise ValidationFailed(f"language must be one of {', '.join(LANGUAGES)}")
    if voice_persona and voice_persona not in VOICE_PERSONAS:
        raise ValidationFailed(f"voicePersona must be one of {', '.join(VOICE_PERSONAS)}")


async def draft_agent(db: Db, llm: LlmService, job_id: str) -> AgentDraftDto:
    job = await get_job_doc(db, job_id)
    draft = await llm.draft_agent(job_for_llm(job))
    return AgentDraftDto.model_validate(draft.model_dump())


def _mirror(
    hunar_agent: HunarAgent,
    *,
    job_id: str | None,
    source: str,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = utcnow()
    custom_vars = hunar_agent.custom_variables or extract_variables(
        hunar_agent.agent_prompt, hunar_agent.introduction, hunar_agent.objective
    )
    return {
        "_id": (existing or {}).get("_id") or new_id(),
        "hunar_agent_id": hunar_agent.id,
        "agent_code": hunar_agent.agent_code,
        "name": hunar_agent.name,
        "language": hunar_agent.language,
        "voice_persona": hunar_agent.voice_persona,
        "persona_name": hunar_agent.persona_name,
        "introduction": hunar_agent.introduction or "",
        "objective": hunar_agent.objective or "",
        "agent_prompt": hunar_agent.agent_prompt or "",
        "result_prompt": hunar_agent.result_prompt,
        "result_schema": hunar_agent.result_schema or {},
        "custom_variables": custom_vars,
        "job_id": job_id,
        "status": hunar_agent.status,
        "source": source,
        "created_at": (existing or {}).get("created_at") or now,
        "updated_at": now,
    }


async def create_agent(db: Db, hunar: HunarClient, body: CreateAgentRequest) -> AgentDto:
    _validate_choices(body.language, body.voice_persona)
    if body.job_id:
        await get_job_doc(db, body.job_id)
    created = await hunar.create_agent(
        HunarAgentCreate(
            name=body.name,
            language=body.language,
            voice_persona=body.voice_persona,
            persona_name=body.persona_name or body.voice_persona.title(),
            agent_prompt=body.agent_prompt,
            objective=body.objective,
            introduction=body.introduction,
            result_prompt=body.result_prompt,
            result_schema=body.result_schema,
        )
    )
    # The list/create responses omit prompt text; fetch the detail so the mirror is complete.
    detail = await hunar.get_agent(created.id)
    doc = _mirror(detail, job_id=body.job_id, source=body.source)
    await db.agents.insert_one(doc)
    if body.job_id:
        await db.jobs.update_one(
            {"_id": body.job_id},
            {"$set": {"agent_id": doc["_id"], "status": "active", "updated_at": utcnow()}},
        )
    return AgentDto.model_validate(doc)


async def import_agent(
    db: Db, hunar: HunarClient, hunar_agent_id: str, job_id: str | None
) -> AgentDto:
    existing_raw = await db.agents.find_one({"hunar_agent_id": hunar_agent_id})
    existing = as_doc(existing_raw) if existing_raw else None
    detail = await hunar.get_agent(hunar_agent_id)
    doc = _mirror(
        detail,
        job_id=job_id or (existing or {}).get("job_id"),
        source="imported",
        existing=existing,
    )
    await db.agents.replace_one({"_id": doc["_id"]}, doc, upsert=True)
    if job_id:
        await db.jobs.update_one(
            {"_id": job_id}, {"$set": {"agent_id": doc["_id"], "updated_at": utcnow()}}
        )
    return AgentDto.model_validate(doc)


async def list_agents(db: Db, job_id: str | None = None) -> list[AgentDto]:
    q: dict[str, Any] = {"job_id": job_id} if job_id else {}
    docs = await db.agents.find(q).sort("created_at", -1).to_list(length=200)
    return [AgentDto.model_validate(d) for d in docs]


async def get_agent_doc(db: Db, agent_id: str) -> dict[str, Any]:
    doc = await db.agents.find_one({"_id": agent_id})
    if not doc:
        raise AgentNotFound(f"Agent {agent_id} not found")
    return as_doc(doc)


async def get_agent(db: Db, agent_id: str) -> AgentDto:
    return AgentDto.model_validate(await get_agent_doc(db, agent_id))


async def refresh_agent(db: Db, hunar: HunarClient, agent_id: str) -> AgentDto:
    doc = await get_agent_doc(db, agent_id)
    detail = await hunar.get_agent(doc["hunar_agent_id"])
    fresh = _mirror(
        detail, job_id=doc.get("job_id"), source=doc.get("source", "manual"), existing=doc
    )
    await db.agents.replace_one({"_id": doc["_id"]}, fresh)
    return AgentDto.model_validate(fresh)


async def update_agent(
    db: Db, hunar: HunarClient, agent_id: str, body: UpdateAgentRequest
) -> AgentDto:
    doc = await get_agent_doc(db, agent_id)
    _validate_choices(body.language, body.voice_persona)
    changes = body.model_dump(exclude_unset=True)
    job_id = changes.pop("job_id", doc.get("job_id"))
    if changes:
        await hunar.update_agent(doc["hunar_agent_id"], HunarAgentUpdate(**changes))
    detail = await hunar.get_agent(doc["hunar_agent_id"])
    fresh = _mirror(detail, job_id=job_id, source=doc.get("source", "manual"), existing=doc)
    await db.agents.replace_one({"_id": doc["_id"]}, fresh)
    if job_id:
        await db.jobs.update_one(
            {"_id": job_id}, {"$set": {"agent_id": doc["_id"], "updated_at": utcnow()}}
        )
    return AgentDto.model_validate(fresh)


async def delete_agent(db: Db, agent_id: str) -> None:
    """Hunar has no delete endpoint; we only drop our mirror and detach it from jobs."""
    await get_agent_doc(db, agent_id)
    await db.agents.delete_one({"_id": agent_id})
    await db.jobs.update_many(
        {"agent_id": agent_id}, {"$set": {"agent_id": None, "updated_at": utcnow()}}
    )

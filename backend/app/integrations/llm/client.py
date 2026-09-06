"""LLM access through OpenRouter (OpenAI-compatible).

There is deliberately no fallback implementation here. With no key, or with the account out
of credit, the language-model features refuse with an error naming the cause; they never
degrade into keyword matching that produces model-shaped output nobody can tell apart.
Tests inject `tests/stub_llm.py`.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Protocol, TypeVar

import httpx
import structlog
from pydantic import BaseModel, ValidationError

from app.core.errors import LlmCredentialRejected, LlmError, LlmQuotaExhausted
from app.integrations.llm import prompts
from app.integrations.llm.schemas import (
    AgentDraft,
    CallAssessment,
    ParsedJob,
    Transcript,
)

log = structlog.get_logger()
T = TypeVar("T", bound=BaseModel)


class LlmService(Protocol):
    enabled: bool

    async def parse_job(self, description: str) -> ParsedJob: ...
    async def draft_agent(self, job: dict[str, Any]) -> AgentDraft: ...
    async def assess_call(
        self, job: dict[str, Any], result: dict[str, Any], transcript: str | None
    ) -> CallAssessment: ...
    async def transcribe(self, recording_url: str) -> Transcript: ...


def _classify(exc: Exception) -> LlmError:
    """Name the real cause, so an empty wallet never looks like a bug in this app."""
    status = getattr(exc, "status_code", None)
    if status == 401 or status == 403:
        return LlmCredentialRejected(
            "OpenRouter rejected the API key. Check OPENROUTER_API_KEY is valid and active."
        )
    if status == 402:
        return LlmQuotaExhausted(
            "The OpenRouter account is out of credit. Top it up to re-enable these features."
        )
    if status == 429:
        return LlmQuotaExhausted(
            "OpenRouter is rate limiting this key. Wait a moment and try again."
        )
    if status == 404:
        return LlmError(f"OpenRouter does not recognise the configured model: {exc}")
    return LlmError(f"LLM request failed: {exc}")


def _extract_json(text: str) -> Any:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


class OpenRouterLlm:
    enabled = True

    def __init__(self, api_key: str, base_url: str, model: str, audio_model: str, app_name: str):
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers={"HTTP-Referer": "https://github.com", "X-Title": app_name},
            timeout=120,
        )
        self._model = model
        self._audio_model = audio_model

    async def _json(
        self, model_cls: type[T], *, system: str, user: Any, model: str | None = None
    ) -> T:
        messages: list[Any] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                resp = await self._client.chat.completions.create(
                    model=model or self._model,
                    messages=messages,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                content = resp.choices[0].message.content or ""
                return model_cls.model_validate(_extract_json(content))
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                log.warning("llm_bad_json", attempt=attempt, error=str(exc)[:300])
                messages.append(
                    {"role": "user", "content": f"Invalid JSON ({exc}). Return only valid JSON."}
                )
            except Exception as exc:  # network / provider errors
                raise _classify(exc) from exc
        raise LlmError(f"LLM returned invalid JSON: {last_error}")

    async def parse_job(self, description: str) -> ParsedJob:
        return await self._json(
            ParsedJob, system=prompts.PARSE_JOB_SYSTEM, user=prompts.parse_job_user(description)
        )

    async def draft_agent(self, job: dict[str, Any]) -> AgentDraft:
        draft = await self._json(
            AgentDraft, system=prompts.DRAFT_AGENT_SYSTEM, user=prompts.draft_agent_user(job)
        )
        return _sanitize_draft(draft)

    async def assess_call(
        self, job: dict[str, Any], result: dict[str, Any], transcript: str | None
    ) -> CallAssessment:
        return await self._json(
            CallAssessment,
            system=prompts.ASSESS_CALL_SYSTEM,
            user=prompts.assess_call_user(job, result, transcript),
        )

    async def transcribe(self, recording_url: str) -> Transcript:
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.get(recording_url)
        if resp.status_code != 200:
            raise LlmError(f"Could not download recording (HTTP {resp.status_code})")
        fmt = "wav" if recording_url.lower().endswith(".wav") else "mp3"
        audio_b64 = base64.b64encode(resp.content).decode()
        user_content = [
            {"type": "text", "text": "Transcribe this call."},
            {"type": "input_audio", "input_audio": {"data": audio_b64, "format": fmt}},
        ]
        return await self._json(
            Transcript, system=prompts.TRANSCRIBE_SYSTEM, user=user_content, model=self._audio_model
        )


_ALLOWED_VARS = {"persona_name", "candidate_name", "job_role", "company", "location"}


def _sanitize_draft(draft: AgentDraft) -> AgentDraft:
    """Guarantee the draft only uses variables our call layer can fill."""

    def fix(text: str) -> str:
        return re.sub(
            r"{(\w+)}", lambda m: m.group(0) if m.group(1) in _ALLOWED_VARS else m.group(1), text
        )

    draft.introduction = fix(draft.introduction)
    draft.agent_prompt = fix(draft.agent_prompt)
    draft.objective = fix(draft.objective)
    draft.result_prompt = fix(draft.result_prompt)
    draft.voice_persona = draft.voice_persona.upper()
    if draft.voice_persona not in {"NEHA", "ROY", "ZOE", "SAM", "MIRA", "EESHA"}:
        draft.voice_persona = "NEHA"
    draft.language = draft.language.upper()
    if not draft.result_schema:
        draft.result_schema = {
            "summary": "string",
            "interested": "boolean",
        }
    draft.name = draft.name[:64]
    return draft

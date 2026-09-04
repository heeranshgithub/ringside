"""LLM access through OpenRouter (OpenAI-compatible). One Protocol, a real client, and a
deterministic fallback used in tests and when no key is configured."""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Protocol, TypeVar

import httpx
import structlog
from pydantic import BaseModel, ValidationError

from app.core.errors import LlmError
from app.integrations.llm import prompts
from app.integrations.llm.schemas import (
    AgentDraft,
    CallAssessment,
    ParsedJob,
    ParsedSearchCriteria,
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
                raise LlmError(f"LLM request failed: {exc}") from exc
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
            "recommendation": "string",
        }
    draft.name = draft.name[:64]
    return draft


class RuleBasedLlm:
    """No-key fallback. Deterministic, good enough to keep the product usable and testable."""

    enabled = False

    async def parse_job(self, description: str) -> ParsedJob:
        lines = [ln.strip() for ln in description.strip().splitlines() if ln.strip()]
        first = lines[0] if lines else "Untitled role"
        # "Senior Engineer - Acme, Bengaluru" -> title "Senior Engineer", company "Acme"
        dashes = "\u2014\u2013|@"  # em dash, en dash, pipe, at (hyphen added last)
        title = (
            re.split(rf"\s+[{dashes},-]\s+|\s+at\s+", first, maxsplit=1)[0].strip()[:80]
            or first[:80]
        )
        company = None
        m = re.search(rf"\s+[{dashes}-]\s+([^,|]+?)(?:,|$)", first)
        if m:
            company = m.group(1).strip()[:80]
        low = description.lower()
        known_skills = [
            "python",
            "fastapi",
            "django",
            "node.js",
            "typescript",
            "react",
            "next.js",
            "aws",
            "docker",
            "kubernetes",
            "sql",
            "postgres",
            "mongodb",
            "java",
            "go",
            "sales",
            "crm",
            "excel",
            "hindi",
            "english",
            "tamil",
            "kannada",
            "telugu",
            "marketing",
            "seo",
            "customer support",
        ]
        skills = [s for s in known_skills if s in low]
        cities = [
            "bengaluru",
            "bangalore",
            "mumbai",
            "delhi",
            "hyderabad",
            "chennai",
            "pune",
            "gurugram",
            "noida",
            "kolkata",
            "ahmedabad",
            "remote",
        ]
        locations = [c.title() for c in cities if c in low]
        seniority = (
            "senior"
            if "senior" in low or "lead" in low
            else "entry"
            if "fresher" in low or "junior" in low
            else None
        )
        questions = [
            "Are you currently open to new opportunities?",
            "How many years of relevant experience do you have?",
            "Which city are you based in, and are you open to relocation?",
            "What is your current and expected salary?",
            "What is your notice period or earliest joining date?",
        ]
        return ParsedJob(
            title=title,
            company=company,
            location=locations[0] if locations else None,
            seniority=seniority,
            summary=" ".join(lines[1:4])[:400],
            must_haves=skills[:6],
            screening_questions=questions,
            search_criteria=ParsedSearchCriteria(
                titles=[title],
                locations=locations[:3],
                skills=skills[:8],
                seniorities=[seniority] if seniority else [],
                keywords=title,
            ),
        )

    async def draft_agent(self, job: dict[str, Any]) -> AgentDraft:
        questions = job.get("screening_questions") or []
        q_text = "\n".join(f"- {q}" for q in questions) or "- Are you interested in this role?"
        return AgentDraft(
            name=f"Screener: {job.get('title', 'Role')}"[:64],
            persona_name="Neha",
            voice_persona="NEHA",
            language="ENGLISH",
            introduction=(
                "Hi {candidate_name}, this is {persona_name} calling from the hiring team at "
                "{company} about the {job_role} position. Is this a good time for a two-minute "
                "chat?"
            ),
            objective=(
                "Screen the candidate for the {job_role} role at {company} and collect "
                "structured hiring signals."
            ),
            agent_prompt=(
                "You are {persona_name}, a polite and efficient recruiting assistant for "
                "{company}. You are calling {candidate_name} about the {job_role} role based in "
                "{location}. Ask one question at a time, confirm key facts by repeating them, "
                "keep the call under four minutes, and speak simply. If the candidate is busy or "
                "not interested, thank them and end the call politely. Cover these questions:\n"
                + q_text
            ),
            result_prompt=(
                "From the conversation, extract a JSON object matching the schema. Use "
                '"unknown" when a fact was not discussed. recommendation must be hire_now, '
                "maybe, reject or unknown."
            ),
            result_schema={
                "summary": "string",
                "interested": "boolean",
                "years_experience": "string",
                "current_location": "string",
                "open_to_relocation": "boolean",
                "current_ctc": "string",
                "expected_ctc": "string",
                "notice_period_days": "string",
                "recommendation": "string",
            },
        )

    async def assess_call(
        self, job: dict[str, Any], result: dict[str, Any], transcript: str | None
    ) -> CallAssessment:
        known = {
            k: v
            for k, v in result.items()
            if str(v).lower() not in {"unknown", "not available", "", "none"}
        }
        if not known:
            return CallAssessment(
                fit_score=5,
                recommendation="insufficient_data",
                headline="No usable answers captured.",
            )
        interested = str(result.get("interested", "")).lower() in {"true", "yes", "interested"}
        rec = str(result.get("recommendation", "")).lower()
        score = (
            40
            + (25 if interested else -20)
            + (25 if rec == "hire_now" else 5 if rec == "maybe" else -25 if rec == "reject" else 0)
        )
        score = max(0, min(100, score))
        label = (
            "strong_yes"
            if score >= 80
            else "yes"
            if score >= 60
            else "maybe"
            if score >= 40
            else "no"
        )
        return CallAssessment(
            fit_score=score,
            recommendation=label,
            headline=str(result.get("summary") or "Screening completed.")[:160],
            strengths=[f"{k}: {v}" for k, v in list(known.items())[:4]],
            concerns=[] if interested else ["Candidate did not confirm interest."],
            next_step="Schedule technical interview" if score >= 60 else "Keep in pipeline",
        )

    async def transcribe(self, recording_url: str) -> Transcript:
        raise LlmError("Transcription requires an OpenRouter API key (OPENROUTER_API_KEY).")

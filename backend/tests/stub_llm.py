"""A test double for the language model.

This is deliberately *not* shipped in `app/`. The product has no rule-based fallback: with
no key, LLM features refuse. But the test suite must still run offline with no key and no
network, so it injects this instead.

Keeping it under `tests/` is the whole point. A stand-in that lives in application code
eventually gets reached by a misconfiguration; one that lives here cannot be.
"""

from __future__ import annotations

from typing import Any

from app.integrations.llm.schemas import (
    AgentDraft,
    CallAssessment,
    ParsedJob,
    ParsedSearchCriteria,
    Transcript,
)


class StubLlm:
    """Fixed, obviously-synthetic answers. Never asserts anything about real quality."""

    enabled = True

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def parse_job(self, description: str) -> ParsedJob:
        self.calls.append("parse_job")
        return ParsedJob(
            title="Senior Frontend Engineer (Next.js)",
            company="Northline Labs",
            location="Bengaluru",
            seniority="senior",
            summary="Own the recruiter-facing dashboard.",
            must_haves=["react", "typescript"],
            nice_to_haves=["playwright"],
            screening_questions=[
                "Are you open to new opportunities?",
                "How many years of React experience do you have?",
                "What is your notice period?",
            ],
            search_criteria=ParsedSearchCriteria(
                titles=["Senior Frontend Engineer"],
                locations=["Bengaluru"],
                skills=["react", "typescript"],
                seniorities=["senior"],
                keywords="frontend engineer",
            ),
        )

    async def draft_agent(self, job: dict[str, Any]) -> AgentDraft:
        self.calls.append("draft_agent")
        return AgentDraft(
            name=f"Screener: {job.get('title', 'Role')}"[:64],
            persona_name="Neha",
            voice_persona="NEHA",
            language="ENGLISH",
            introduction=(
                "Hi {candidate_name}, this is {persona_name} from {company} about the "
                "{job_role} role. Is now a good time?"
            ),
            objective="Screen the candidate for {job_role} at {company}.",
            agent_prompt=(
                "You are {persona_name}, screening {candidate_name} for the {job_role} role "
                "at {company} in {location}. Ask one question at a time."
            ),
            result_prompt='Extract the answers as JSON. Use "unknown" when not discussed.',
            result_schema={
                "summary": "string",
                "interested": "boolean",
                "recommendation": "string",
            },
        )

    async def assess_call(
        self, job: dict[str, Any], result: dict[str, Any], transcript: str | None
    ) -> CallAssessment:
        self.calls.append("assess_call")
        return CallAssessment(
            fit_score=72,
            recommendation="yes",
            headline="Stub assessment.",
            strengths=["Stub strength"],
            concerns=[],
            next_step="Schedule technical round",
        )

    async def transcribe(self, recording_url: str) -> Transcript:
        self.calls.append("transcribe")
        return Transcript(
            language="English",
            turns=[{"speaker": "agent", "text": "Stub line."}],
            text="Agent: Stub line.",
        )

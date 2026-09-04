"""Hunar Voice Agents API client + the Protocol the app codes against + an offline fake."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

import httpx
import structlog

from app.core.errors import HunarApiError
from app.integrations.hunar.schemas import (
    HunarAgent,
    HunarAgentCreate,
    HunarAgentUpdate,
    HunarBulkCallCreate,
    HunarCall,
    HunarCallCreate,
    HunarCallCreated,
    HunarNumber,
    Paginated,
)

log = structlog.get_logger()


class HunarClient(Protocol):
    async def list_agents(self, *, page: int = 1, page_size: int = 20) -> Paginated: ...
    async def get_agent(self, agent_id: str) -> HunarAgent: ...
    async def create_agent(self, body: HunarAgentCreate) -> HunarAgent: ...
    async def update_agent(self, agent_id: str, body: HunarAgentUpdate) -> HunarAgent: ...
    async def create_call(self, body: HunarCallCreate) -> HunarCallCreated: ...
    async def create_calls_bulk(self, body: HunarBulkCallCreate) -> list[HunarCallCreated]: ...
    async def get_call(self, call_id: str) -> HunarCall: ...
    async def list_calls(
        self,
        *,
        agent_ids: list[str] | None = None,
        statuses: list[str] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Paginated: ...
    async def list_numbers(self) -> list[HunarNumber]: ...
    async def aclose(self) -> None: ...


class HttpHunarClient:
    def __init__(self, api_key: str, base_url: str, *, timeout: float = 30.0):
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kw: Any) -> Any:
        try:
            resp = await self._http.request(method, path, **kw)
        except httpx.HTTPError as exc:
            raise HunarApiError(0, f"Hunar request failed: {exc}") from exc
        if resp.status_code >= 400:
            try:
                payload = resp.json()
            except ValueError:
                payload = {"message": resp.text[:500]}
            message = (
                payload.get("message") or payload.get("detail") or f"Hunar HTTP {resp.status_code}"
                if isinstance(payload, dict)
                else f"Hunar HTTP {resp.status_code}"
            )
            log.warning("hunar_error", status=resp.status_code, path=path, payload=payload)
            raise HunarApiError(resp.status_code, str(message), payload)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def list_agents(self, *, page: int = 1, page_size: int = 20) -> Paginated:
        data = await self._request("GET", "agents/", params={"page": page, "page_size": page_size})
        return Paginated.model_validate(data)

    async def get_agent(self, agent_id: str) -> HunarAgent:
        return HunarAgent.model_validate(await self._request("GET", f"agents/{agent_id}/"))

    async def create_agent(self, body: HunarAgentCreate) -> HunarAgent:
        data = await self._request("POST", "agents/", json=body.model_dump(exclude_none=True))
        return HunarAgent.model_validate(data)

    async def update_agent(self, agent_id: str, body: HunarAgentUpdate) -> HunarAgent:
        data = await self._request(
            "PUT", f"agents/{agent_id}/", json=body.model_dump(exclude_none=True)
        )
        return HunarAgent.model_validate(data)

    async def create_call(self, body: HunarCallCreate) -> HunarCallCreated:
        data = await self._request("POST", "calls/", json=body.model_dump(exclude_none=True))
        return HunarCallCreated.model_validate(data)

    async def create_calls_bulk(self, body: HunarBulkCallCreate) -> list[HunarCallCreated]:
        data = await self._request("POST", "calls/bulk/", json=body.model_dump(exclude_none=True))
        return [HunarCallCreated.model_validate(d) for d in data or []]

    async def get_call(self, call_id: str) -> HunarCall:
        return HunarCall.model_validate(await self._request("GET", f"calls/{call_id}/"))

    async def list_calls(
        self,
        *,
        agent_ids: list[str] | None = None,
        statuses: list[str] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Paginated:
        params: list[tuple[str, Any]] = [("page", page), ("page_size", page_size)]
        params += [("agent_id", a) for a in agent_ids or []]
        params += [("status", s) for s in statuses or []]
        return Paginated.model_validate(await self._request("GET", "calls/", params=params))

    async def list_numbers(self) -> list[HunarNumber]:
        data = await self._request("GET", "numbers/", params={"page_size": 50})
        return [HunarNumber.model_validate(n) for n in data.get("results", [])]


class FakeHunarClient:
    """In-memory stand-in. Calls progress to COMPLETED with a canned result when `tick()` runs."""

    def __init__(self, *, auto_complete: bool = True):
        self.agents: dict[str, dict[str, Any]] = {}
        self.calls: dict[str, dict[str, Any]] = {}
        self.auto_complete = auto_complete
        self._agent_seq = 0

    async def aclose(self) -> None:
        return None

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    async def list_agents(self, *, page: int = 1, page_size: int = 20) -> Paginated:
        items = list(self.agents.values())
        return Paginated(count=len(items), results=items[(page - 1) * page_size : page * page_size])

    async def get_agent(self, agent_id: str) -> HunarAgent:
        if agent_id not in self.agents:
            raise HunarApiError(404, "Agent not found")
        return HunarAgent.model_validate(self.agents[agent_id])

    async def create_agent(self, body: HunarAgentCreate) -> HunarAgent:
        import re

        self._agent_seq += 1
        text = " ".join([body.agent_prompt, body.introduction, body.objective])
        variables = sorted({v for v in re.findall(r"{(\w+)}", text) if v != "persona_name"})
        doc = {
            "id": str(uuid4()),
            "status": "ACTIVE",
            **body.model_dump(),
            "persona_name": body.persona_name or body.voice_persona,
            "voice_name": body.voice_persona,
            "summary": body.objective[:160],
            "logo": None,
            "custom_variables": variables,
            "required_variables": ["callee_name", "mobile_number"],
            "agent_code": f"FK{self._agent_seq:02d}",
            "created_at": self._now(),
            "silence_response": "Are you there?",
            "conclusion": "Have a great day.",
        }
        self.agents[doc["id"]] = doc
        return HunarAgent.model_validate(doc)

    async def update_agent(self, agent_id: str, body: HunarAgentUpdate) -> HunarAgent:
        if agent_id not in self.agents:
            raise HunarApiError(404, "Agent not found")
        self.agents[agent_id].update(body.model_dump(exclude_none=True))
        return HunarAgent.model_validate(self.agents[agent_id])

    def _new_call(
        self,
        agent_id: str,
        callee_name: str,
        mobile: str,
        custom: dict[str, str],
        request_id: str | None,
    ) -> dict[str, Any]:
        if agent_id not in self.agents:
            raise HunarApiError(404, "Agent not found")
        agent = self.agents[agent_id]
        missing = [v for v in agent["custom_variables"] if v not in custom]
        if missing:
            raise HunarApiError(400, f"Custom data keys are not present: {missing}")
        doc: dict[str, Any] = {
            "id": str(uuid4()),
            "request_id": request_id or str(uuid4()),
            "status": "SCHEDULED",
            "lifecycle_status": "IN_PROGRESS",
            "callee_name": callee_name,
            "mobile_number": mobile,
            "agent_id": agent_id,
            "language": agent.get("language", "ENGLISH"),
            "call_type": "INDIVIDUAL",
            "custom_data": custom,
            "system_data": {},
            "duration_seconds": 0.0,
            "duration_minutes": 0.0,
            "user_speech_duration": 0.0,
            "engagement_status": None,
            "answered_by": None,
            "call_ended_by": None,
            "recording_url": None,
            "result": {},
            "created_at": self._now(),
            "updated_at": self._now(),
            "started_at": None,
            "ended_at": None,
            "max_retries": 0,
            "retry_count": 0,
            "retries_left": 0,
            "timezone": "Asia/Kolkata",
            "from_phone_number": "+910000000000",
        }
        self.calls[doc["id"]] = doc
        return doc

    async def create_call(self, body: HunarCallCreate) -> HunarCallCreated:
        doc = self._new_call(
            body.agent_id, body.callee_name, body.mobile_number, body.custom_data, body.request_id
        )
        return HunarCallCreated.model_validate(doc)

    async def create_calls_bulk(self, body: HunarBulkCallCreate) -> list[HunarCallCreated]:
        out = []
        for r in body.data:
            doc = self._new_call(
                body.agent_id, r.callee_name, r.mobile_number, r.custom_data, body.request_id
            )
            out.append(HunarCallCreated.model_validate(doc))
        return out

    async def get_call(self, call_id: str) -> HunarCall:
        if call_id not in self.calls:
            raise HunarApiError(404, "Call not found")
        if self.auto_complete:
            self.tick(call_id)
        return HunarCall.model_validate(self.calls[call_id])

    def tick(self, call_id: str) -> None:
        """Advance a fake call to a completed, engaged state with a plausible result."""
        doc = self.calls[call_id]
        if doc["lifecycle_status"] in ("COMPLETED", "FAILED"):
            return
        agent = self.agents.get(doc["agent_id"], {})
        schema = agent.get("result_schema", {}) or {}
        props = schema.get("properties", schema) if isinstance(schema, dict) else {}
        result = {k: f"sample {k.replace('_', ' ')}" for k in props}
        result.setdefault("summary", "Candidate is interested and available to join in 30 days.")
        doc.update(
            status="COMPLETED",
            lifecycle_status="COMPLETED",
            engagement_status="ENGAGED",
            answered_by="HUMAN",
            call_ended_by="AGENT",
            duration_seconds=84.0,
            duration_minutes=1.4,
            user_speech_duration=31.2,
            recording_url=f"https://example.invalid/recordings/{call_id}.wav",
            result=result,
            started_at=self._now(),
            ended_at=self._now(),
            updated_at=self._now(),
        )

    async def list_calls(self, *, agent_ids=None, statuses=None, page=1, page_size=50) -> Paginated:
        items = [
            c
            for c in self.calls.values()
            if (not agent_ids or c["agent_id"] in agent_ids)
            and (not statuses or c["status"] in statuses)
        ]
        return Paginated(count=len(items), results=items[(page - 1) * page_size : page * page_size])

    async def list_numbers(self) -> list[HunarNumber]:
        await asyncio.sleep(0)
        return []

"""A missing credential must refuse, never simulate.

The failure this guards against: an in-memory simulator returns ids and agent codes that
look exactly like real ones, so a misconfigured deployment reports success and changes
nothing in the world. Tests may inject the simulators; forgetting a key must not reach them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.integrations.hunar.client import FakeHunarClient
from app.integrations.llm.client import RuleBasedLlm
from app.main import _build_hunar, _build_llm, create_app


def settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, env="dev", mongodb_uri="mongodb://unused", **overrides)  # type: ignore[arg-type]


async def app_client(s: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(s, db=AsyncMongoMockClient()["t"])
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


class TestNoSimulatorByAccident:
    def test_missing_hunar_key_does_not_yield_the_fake(self) -> None:
        assert not isinstance(_build_hunar(settings()), FakeHunarClient)

    def test_missing_llm_key_does_not_yield_the_rule_based_parser(self) -> None:
        assert not isinstance(_build_llm(settings()), RuleBasedLlm)

    def test_the_offline_parser_requires_an_explicit_opt_in(self) -> None:
        assert isinstance(_build_llm(settings(allow_degraded_llm=True)), RuleBasedLlm)


class TestRefusals:
    async def test_creating_an_agent_without_a_hunar_key_is_refused(self) -> None:
        async for client in app_client(settings(openrouter_api_key="x")):
            resp = await client.post(
                "/api/agents",
                json={
                    "name": "Screener",
                    "language": "ENGLISH",
                    "voicePersona": "NEHA",
                    "introduction": "Hi there, this is a screening call.",
                    "objective": "Screen the candidate.",
                    "agentPrompt": "Ask the candidate about their experience and notice period.",
                    "resultPrompt": "Extract the answers as JSON.",
                    "resultSchema": {"summary": "string"},
                },
            )
            assert resp.status_code == 503
            body = resp.json()["error"]
            assert body["code"] == "credential_missing"
            assert "HUNAR_API_KEY" in body["message"]

    async def test_parsing_a_job_without_an_llm_key_is_refused(self) -> None:
        async for client in app_client(settings(hunar_api_key="x")):
            resp = await client.post("/api/jobs/parse", json={"description": "A" * 40})
            assert resp.status_code == 503
            assert resp.json()["error"]["code"] == "credential_missing"
            assert "OPENROUTER_API_KEY" in resp.json()["error"]["message"]

    async def test_the_opt_in_parser_works_and_says_it_is_not_a_model(self) -> None:
        s = settings(hunar_api_key="x", allow_degraded_llm=True)
        async for client in app_client(s):
            resp = await client.post(
                "/api/jobs/parse",
                json={"description": "Senior Python developer in Bengaluru with FastAPI. " * 2},
            )
            assert resp.status_code == 200
            assert resp.json()["llmUsed"] is False


class TestCapabilityReport:
    @pytest.mark.parametrize(
        ("overrides", "key", "expected"),
        [
            ({}, "hunar", "missing"),
            ({"hunar_api_key": "x"}, "hunar", "ok"),
            ({}, "llm", "missing"),
            ({"allow_degraded_llm": True}, "llm", "degraded"),
            ({"openrouter_api_key": "x"}, "llm", "ok"),
            ({}, "dialling", "missing"),
            ({"test_phone_numbers": "+919999900000"}, "dialling", "ok"),
            ({}, "people_search", "degraded"),
            ({"pdl_api_key": "x"}, "people_search", "ok"),
            ({}, "webhooks", "degraded"),
            ({"public_base_url": "https://x.example"}, "webhooks", "ok"),
        ],
    )
    async def test_each_capability_reports_its_real_state(
        self, overrides: dict[str, object], key: str, expected: str
    ) -> None:
        async for client in app_client(settings(**overrides)):
            caps = (await client.get("/api/config")).json()["capabilities"]
            state = next(c["state"] for c in caps if c["key"] == key)
            assert state == expected, f"{key} with {overrides}"

    async def test_a_missing_capability_names_the_variable_to_set(self) -> None:
        async for client in app_client(settings()):
            caps = (await client.get("/api/config")).json()["capabilities"]
            missing = {c["key"]: c["envVar"] for c in caps if c["state"] == "missing"}
            assert missing["hunar"] == "HUNAR_API_KEY"
            assert missing["llm"] == "OPENROUTER_API_KEY"
            assert missing["dialling"] == "TEST_PHONE_NUMBERS"

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
from app.core.unconfigured import UnconfiguredLlm
from app.integrations.hunar.client import FakeHunarClient
from app.main import _build_hunar, _build_llm, create_app


def settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, env="dev", mongodb_uri="mongodb://unused", **overrides)  # type: ignore[arg-type]


async def app_client(s: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(s, db=AsyncMongoMockClient()["t"])
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        # Setting an access code also gates /api, so carry it or every read is a 401.
        headers = {"X-Access-Code": s.app_access_code} if s.app_access_code else {}
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            yield c


class TestNoSimulatorByAccident:
    def test_missing_hunar_key_does_not_yield_the_fake(self) -> None:
        assert not isinstance(_build_hunar(settings()), FakeHunarClient)

    def test_missing_llm_key_yields_a_refusing_stand_in(self) -> None:
        llm = _build_llm(settings())
        assert isinstance(llm, UnconfiguredLlm)
        assert llm.enabled is False

    def test_no_degraded_llm_implementation_ships_in_the_app(self) -> None:
        """There is no keyword-matching fallback to fall into, by flag or otherwise."""
        import app.integrations.llm.client as llm_module
        from app.modules.jobs.schemas import ParsedJobDto

        assert not hasattr(llm_module, "RuleBasedLlm")
        assert not hasattr(Settings(_env_file=None), "allow_degraded_llm")
        # Nothing on the wire asks "was this really the model?" either: a field that is
        # always true is an invitation to write the branch that handles false.
        assert "llm_used" not in ParsedJobDto.model_fields


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

    async def test_scoring_a_call_without_an_llm_key_is_refused(self) -> None:
        """The worst fallback was an invented fit score, so prove it cannot happen."""
        async for client in app_client(settings(hunar_api_key="x")):
            resp = await client.post("/api/calls/does-not-exist/assess")
            # Either the call is missing or the LLM refuses; what must never happen is a score.
            assert resp.status_code in (404, 503)
            assert "fitScore" not in resp.text


class TestCapabilityReport:
    @pytest.mark.parametrize(
        ("overrides", "key", "expected"),
        [
            ({}, "hunar", "missing"),
            ({"hunar_api_key": "x"}, "hunar", "ok"),
            ({}, "llm", "missing"),
            ({"openrouter_api_key": "x"}, "llm", "ok"),
            ({}, "dialling", "missing"),
            ({"app_access_code": "shh"}, "dialling", "ok"),
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
            # No number can be nominated without a gate, so that is the thing to set.
            assert missing["dialling"] == "APP_ACCESS_CODE"


class TestRuntimeFailuresAreNamed:
    """A key that exists but stops working must not look like an app bug."""

    @pytest.mark.parametrize(
        ("status", "code", "phrase"),
        [
            (401, "llm_credential_rejected", "rejected the API key"),
            (403, "llm_credential_rejected", "rejected the API key"),
            (402, "llm_quota_exhausted", "out of credit"),
            (429, "llm_quota_exhausted", "rate limiting"),
            (404, "llm_error", "does not recognise the configured model"),
            (500, "llm_error", "LLM request failed"),
        ],
    )
    def test_provider_status_maps_to_a_specific_error(
        self, status: int, code: str, phrase: str
    ) -> None:
        from app.integrations.llm.client import _classify

        exc = Exception("upstream said no")
        exc.status_code = status  # type: ignore[attr-defined]
        err = _classify(exc)
        assert err.code == code
        assert phrase in err.message

    def test_an_exhausted_quota_is_a_503_not_a_500(self) -> None:
        from app.core.errors import LlmQuotaExhausted

        assert LlmQuotaExhausted().status_code == 503

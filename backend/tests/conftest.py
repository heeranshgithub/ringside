from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.integrations.hunar.client import FakeHunarClient
from app.integrations.people.mock import MockProvider
from app.main import create_app
from tests.stub_llm import StubLlm

TEST_KEY = "test-hunar-key"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,  # never read the developer's .env
        env="test",
        mongodb_uri="mongodb://unused",
        mongodb_db="test",
        hunar_api_key=TEST_KEY,
        safe_dial_mode=True,
        test_phone_numbers="+919999900000",  # type: ignore[call-arg]
        poller_enabled=False,
        openrouter_api_key="",
    )


@pytest.fixture
def hunar() -> FakeHunarClient:
    return FakeHunarClient()


@pytest.fixture
async def client(settings: Settings, hunar: FakeHunarClient) -> AsyncIterator[AsyncClient]:
    db = AsyncMongoMockClient()["test"]
    app = create_app(
        settings, db=db, hunar=hunar, llm=StubLlm(), providers={"mock": MockProvider()}
    )
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


JD = """Senior Frontend Engineer (Next.js)
Bengaluru, India. 5+ years with React, TypeScript, Next.js and Tailwind.
You will own the hiring dashboard UI. Nice to have: Redux, testing with Playwright."""


async def make_job(client: AsyncClient) -> dict:
    parsed = (await client.post("/api/jobs/parse", json={"description": JD})).json()
    body = {k: v for k, v in parsed.items() if k != "llmUsed"}
    body.update({"description": JD, "company": "Acme"})
    resp = await client.post("/api/jobs", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def make_agent(client: AsyncClient, job_id: str) -> dict:
    draft = (await client.post("/api/agents/draft", json={"jobId": job_id})).json()
    body = {k: v for k, v in draft.items() if k != "llmUsed"}
    body["jobId"] = job_id
    resp = await client.post("/api/agents", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def make_candidate(client: AsyncClient, job_id: str, **extra) -> dict:
    body = {"jobId": job_id, "name": "Ananya Iyer", "phone": "9876543210", **extra}
    resp = await client.post("/api/candidates", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()

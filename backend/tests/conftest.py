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
ACCESS_CODE = "test-access-code"
SESSION = "conftest-session-0001"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,  # never read the developer's .env
        env="test",
        mongodb_uri="mongodb://unused",
        mongodb_db="test",
        hunar_api_key=TEST_KEY,
        safe_dial_mode=True,
        # Safe dial has no server-side number to fall back on, so a test that places a call
        # verifies a number the way a visitor does. That needs the gate, which client dialling
        # refuses to arm without.
        app_access_code=ACCESS_CODE,
        allow_client_dial_target=True,
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
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"X-Access-Code": ACCESS_CODE, "X-Session-Id": SESSION},
        ) as c:
            yield c


JD = """Senior Frontend Engineer (Next.js)
Bengaluru, India. 5+ years with React, TypeScript, Next.js and Tailwind.
You will own the hiring dashboard UI. Nice to have: Redux, testing with Playwright."""


async def make_job(client: AsyncClient) -> dict:
    body = (await client.post("/api/jobs/parse", json={"description": JD})).json()
    body.update({"description": JD, "company": "Acme"})
    resp = await client.post("/api/jobs", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def make_agent(client: AsyncClient, job_id: str) -> dict:
    body = (await client.post("/api/agents/draft", json={"jobId": job_id})).json()
    body["jobId"] = job_id
    resp = await client.post("/api/agents", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def make_candidate(client: AsyncClient, job_id: str, **extra) -> dict:
    body = {"jobId": job_id, "name": "Ananya Iyer", "phone": "9876543210", **extra}
    resp = await client.post("/api/candidates", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def verify_dial_target(
    client: AsyncClient, hunar: FakeHunarClient, phone: str = "98765 43210"
) -> str:
    """Take a number through the real verification round trip and return it in E.164.

    Safe dial rings only a number someone proved is theirs, so any test that places a call
    has to earn a destination first — exactly as the UI does.
    """
    started = await client.post("/api/dial-target/start", json={"phone": phone, "consent": True})
    assert started.status_code == 201, started.text
    placed = list(hunar.calls.values())[-1]
    code = placed["custom_data"]["code"].replace(" ", "")
    confirmed = await client.post(
        f"/api/dial-target/{started.json()['id']}/confirm", json={"code": code}
    )
    assert confirmed.status_code == 200, confirmed.text
    return str(placed["mobile_number"])

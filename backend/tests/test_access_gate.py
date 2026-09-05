"""Which routes are reachable without the access code.

This is a whole-surface assertion rather than a per-route one on purpose: the risk is not
that an existing endpoint loses its guard, it is that a new router gets mounted outside the
gated one and nobody notices. Adding a route to the app makes this test fail until the
route is either gated or added to the allowlist deliberately.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.integrations.hunar.client import FakeHunarClient
from app.integrations.llm.client import RuleBasedLlm
from app.main import create_app

CODE = "test-access-code"

# Everything else must answer 401 without the code. These two cannot:
#   /health          the platform's health check runs before any credential exists
#   /webhooks/hunar  Hunar cannot send a header we invented; it is protected by the
#                    HMAC signature instead, which is checked in test_flow.py
UNGATED = {"/health", "/webhooks/hunar"}


def _settings() -> Settings:
    return Settings(
        _env_file=None,  # never read the developer's .env
        env="test",
        mongodb_uri="mongodb://unused",
        hunar_api_key="k",
        app_access_code=CODE,
        poller_enabled=False,
    )


@asynccontextmanager
async def _app() -> AsyncIterator[tuple[AsyncClient, list[tuple[str, str]]]]:
    """Yields the client and every (method, path) the app publishes.

    Read from the OpenAPI schema rather than `app.routes`: this FastAPI keeps included
    routers nested instead of flattening them, so walking `app.routes` silently sees only
    the handful defined on the app itself, which is exactly the blind spot this test exists
    to close.
    """
    app = create_app(
        _settings(),
        db=AsyncMongoMockClient()["t"],
        hunar=FakeHunarClient(),
        llm=RuleBasedLlm(),
    )
    verbs = {"get", "post", "patch", "delete", "put"}
    surface = [
        (method.upper(), path)
        for path, ops in app.openapi()["paths"].items()
        for method in ops
        if method in verbs
    ]
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client,
    ):
        yield client, surface


async def test_every_route_is_gated_except_a_named_two() -> None:
    async with _app() as (client, surface):
        assert len(surface) > 20, "the surface looks truncated; the enumeration is wrong"
        reachable: set[str] = set()
        for method, path in surface:
            resp = await client.request(method, path.replace("{id}", "probe"), json={})
            if resp.status_code != 401:
                reachable.add(path)

        assert reachable == UNGATED, (
            "The set of routes reachable without an access code changed. "
            f"Now reachable: {sorted(reachable)}. Expected: {sorted(UNGATED)}. "
            "A new route belongs under the gated /api router unless it is genuinely "
            "called by something that cannot send our header."
        )


async def test_a_wrong_code_is_not_a_missing_code() -> None:
    async with _app() as (client, _surface):
        assert (await client.get("/api/config")).status_code == 401
        assert (
            await client.get("/api/config", headers={"X-Access-Code": "not-it"})
        ).status_code == 401
        ok = await client.get("/api/config", headers={"X-Access-Code": CODE})
        assert ok.status_code == 200


@pytest.mark.parametrize("env,expect_docs", [("dev", True), ("prod", False)])
def test_interactive_docs_are_not_published_in_production(env: str, expect_docs: bool) -> None:
    settings = Settings(_env_file=None, env=env, mongodb_uri="mongodb://unused", hunar_api_key="k")
    app = create_app(
        settings, db=AsyncMongoMockClient()["t"], hunar=FakeHunarClient(), llm=RuleBasedLlm()
    )
    assert (app.docs_url is not None) is expect_docs

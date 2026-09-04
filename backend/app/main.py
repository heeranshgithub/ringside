"""App factory. Everything external is injectable so tests run fully offline."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.db import Db, ensure_indexes, make_client
from app.core.deps import Container, require_access
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.models import ApiModel
from app.integrations.hunar.client import FakeHunarClient, HttpHunarClient, HunarClient
from app.integrations.llm.client import LlmService, OpenRouterLlm, RuleBasedLlm
from app.integrations.people.apollo import ApolloProvider
from app.integrations.people.base import PeopleProvider
from app.integrations.people.mock import MockProvider
from app.integrations.people.pdl import PdlProvider
from app.modules.agents.router import router as agents_router
from app.modules.calls.router import router as calls_router
from app.modules.candidates.router import router as candidates_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.jobs.router import router as jobs_router
from app.modules.search.router import router as search_router
from app.modules.webhooks.router import router as webhooks_router
from app.workers.poller import run_poller

log = structlog.get_logger()


class HealthDto(ApiModel):
    status: str
    env: str
    version: str


def _build_providers(settings: Settings) -> dict[str, PeopleProvider]:
    providers: dict[str, PeopleProvider] = {"mock": MockProvider()}
    if settings.apollo_api_key:
        providers["apollo"] = ApolloProvider(settings.apollo_api_key)
    if settings.pdl_api_key:
        providers["pdl"] = PdlProvider(settings.pdl_api_key)
    return providers


def _build_llm(settings: Settings) -> LlmService:
    if settings.openrouter_api_key:
        return OpenRouterLlm(
            settings.openrouter_api_key,
            settings.openrouter_base_url,
            settings.llm_model,
            settings.llm_audio_model,
            settings.llm_app_name,
        )
    return RuleBasedLlm()


def _build_hunar(settings: Settings) -> HunarClient:
    if settings.hunar_api_key:
        return HttpHunarClient(settings.hunar_api_key, settings.hunar_base_url)
    log.warning("hunar_key_missing", note="Using FakeHunarClient; calls will be simulated")
    return FakeHunarClient()


def create_app(
    settings: Settings | None = None,
    *,
    db: Db | None = None,
    hunar: HunarClient | None = None,
    llm: LlmService | None = None,
    providers: dict[str, PeopleProvider] | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.env, settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        mongo_client: Any = None
        app_db = db
        if app_db is None:
            mongo_client = make_client(settings.mongodb_uri)
            app_db = mongo_client[settings.mongodb_db]
        container = Container(
            settings=settings,
            db=app_db,
            hunar=hunar or _build_hunar(settings),
            llm=llm or _build_llm(settings),
            providers=providers or _build_providers(settings),
            mongo_client=mongo_client,
        )
        app.state.container = container
        try:
            await ensure_indexes(app_db)
        except Exception as exc:
            log.warning("index_setup_failed", error=str(exc)[:200])
        log.info("startup", config=settings.redact())

        stop = asyncio.Event()
        task: asyncio.Task[None] | None = None
        if settings.poller_enabled and settings.env != "test":
            task = asyncio.create_task(run_poller(container, stop))
        try:
            yield
        finally:
            stop.set()
            if task:
                task.cancel()
            await container.hunar.aclose()
            for p in container.providers.values():
                close = getattr(p, "aclose", None)
                if close:
                    await close()
            if mongo_client is not None:
                mongo_client.close()

    app = FastAPI(
        title="Ringside API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.env != "prod" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"https://.*\.amplifyapp\.com$",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Any:
        rid = request.headers.get("x-request-id") or uuid4().hex[:12]
        request.state.request_id = rid
        structlog.contextvars.bind_contextvars(request_id=rid)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers["x-request-id"] = rid
        return response

    register_error_handlers(app)

    @app.get("/health", response_model=HealthDto, tags=["meta"])
    async def health() -> HealthDto:
        return HealthDto(status="ok", env=settings.env, version=app.version)

    api = APIRouter(prefix="/api", dependencies=[Depends(require_access)])
    api.include_router(jobs_router)
    api.include_router(agents_router)
    api.include_router(candidates_router)
    api.include_router(search_router)
    api.include_router(calls_router)
    api.include_router(dashboard_router)
    app.include_router(api)
    app.include_router(webhooks_router)
    return app


app = create_app()

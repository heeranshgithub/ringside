"""Composition root + FastAPI dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, Header, Request

from app.core.config import Settings
from app.core.db import Db
from app.core.errors import Unauthorized
from app.core.events import EventBus
from app.integrations.hunar.client import HunarClient
from app.integrations.llm.client import LlmService
from app.integrations.people.base import PeopleProvider


@dataclass
class Container:
    settings: Settings
    db: Db
    hunar: HunarClient
    llm: LlmService
    providers: dict[str, PeopleProvider] = field(default_factory=dict)
    events: EventBus = field(default_factory=EventBus)
    mongo_client: Any = None


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_db(c: ContainerDep) -> Db:
    return c.db


def get_settings_dep(c: ContainerDep) -> Settings:
    return c.settings


def get_hunar(c: ContainerDep) -> HunarClient:
    return c.hunar


def get_llm(c: ContainerDep) -> LlmService:
    return c.llm


def get_events(c: ContainerDep) -> EventBus:
    return c.events


DbDep = Annotated[Db, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
HunarDep = Annotated[HunarClient, Depends(get_hunar)]
LlmDep = Annotated[LlmService, Depends(get_llm)]
EventsDep = Annotated[EventBus, Depends(get_events)]

#: The browser identifies itself so a verified number stays scoped to one visitor. Not an
#: identity claim: it decides which number *this* browser may ring, never who anyone is.
SessionId = Annotated[str | None, Header(alias="X-Session-Id")]


async def require_access(
    c: ContainerDep,
    x_access_code: Annotated[str | None, Header(alias="X-Access-Code")] = None,
) -> None:
    expected = c.settings.app_access_code
    if expected and x_access_code != expected:
        raise Unauthorized("This deployment requires an access code.")

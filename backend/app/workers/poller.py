"""Background sync loop: the fallback when Hunar webhooks cannot reach this deployment."""

from __future__ import annotations

import asyncio
import contextlib

import structlog

from app.core.deps import Container
from app.modules.calls.service import sync_pending

log = structlog.get_logger()


async def run_poller(container: Container, stop: asyncio.Event) -> None:
    interval = max(10, container.settings.poller_interval_seconds)
    log.info("poller_started", interval=interval)
    while not stop.is_set():
        try:
            synced, errors = await sync_pending(container.db, container.hunar, container.llm)
            if synced or errors:
                log.info("poller_tick", synced=synced, errors=errors)
        except Exception as exc:
            log.warning("poller_error", error=str(exc)[:300])
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval)
    log.info("poller_stopped")

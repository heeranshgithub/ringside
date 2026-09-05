"""Server-sent events: the last hop, backend to browser.

Webhooks make the upstream hop instant; this makes the downstream one instant too, so a
row in the calls table changes the moment a phone stops ringing instead of on the next
poll. Frames carry an id and nothing else the client needs to trust; the browser refetches
through the normal API, so this stream can be missed or replayed without consequence.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.deps import ContainerDep

log = structlog.get_logger()
router = APIRouter(tags=["events"])

# Long enough to stay quiet, short enough that no proxy calls the connection idle.
HEARTBEAT_SECONDS = 20


@router.get("/events")
async def stream_events(request: Request, c: ContainerDep) -> StreamingResponse:
    queue = c.events.subscribe()

    async def frames() -> AsyncIterator[str]:
        # An immediate comment flushes headers, so the browser knows it is connected.
        yield ": connected\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            raise
        finally:
            c.events.unsubscribe(queue)

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # Tells nginx and App Runner's proxy not to buffer, which would defeat the point.
            "X-Accel-Buffering": "no",
        },
    )

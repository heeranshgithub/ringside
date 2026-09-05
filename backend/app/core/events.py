"""In-process fan-out for live updates.

A call's state changes upstream, we learn about it from a webhook or a poller tick, and
every browser watching should see it immediately rather than on its next refetch. This is
the smallest thing that does that: one queue per connected client, non-blocking writes.

Deliberately in-memory and single-process. It carries notifications, never state: a client
that misses an event still converges, because the event only tells the browser to refetch
and the database remains the source of truth. Running more than one backend instance means
a browser only hears from the instance it is connected to, which is the point at which this
should become Redis pub/sub.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog

log = structlog.get_logger()

# A slow client must never stall the publisher, so its queue is bounded and it gets dropped.
MAX_QUEUED_FRAMES = 64


class EventBus:
    def __init__(self, max_queued: int = MAX_QUEUED_FRAMES) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._max_queued = max_queued

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=self._max_queued)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: str, data: dict[str, Any]) -> None:
        """Fan out one SSE frame. Never awaits, so callers can emit from anywhere."""
        if not self._subscribers:
            return
        frame = f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(frame)
            except asyncio.QueueFull:
                # Backed up past the bound: drop the client and let it reconnect clean.
                self._subscribers.discard(queue)
                log.warning("event_subscriber_dropped", reason="queue_full")

    @property
    def listener_count(self) -> int:
        return len(self._subscribers)

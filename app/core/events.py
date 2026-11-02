import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger("app.events")


class EventBroadcaster:
    """In-memory Server-Sent Events (SSE) broadcaster with connection tracking."""

    def __init__(self) -> None:
        self._listeners: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._listeners.add(q)
        logger.debug("New SSE client subscribed. Active listeners: %d", len(self._listeners))
        return q

    async def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._listeners.discard(q)
        logger.debug("SSE client unsubscribed. Active listeners: %d", len(self._listeners))

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        """Broadcast an event payload to all active SSE subscribers."""
        payload = f"event: {event}\ndata: {json.dumps(data)}\n\n"
        async with self._lock:
            dead_queues = []
            for q in list(self._listeners):
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    dead_queues.append(q)
            for dq in dead_queues:
                self._listeners.discard(dq)
        logger.info("Broadcasted '%s' event to %d listeners", event, len(self._listeners))


broadcaster = EventBroadcaster()

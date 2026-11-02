import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.events import broadcaster

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", summary="Subscribe to Server-Sent Events (SSE)")
async def sse_events(request: Request) -> StreamingResponse:
    """Subscribe to real-time game broadcasts via Server-Sent Events (SSE)."""
    q = await broadcaster.subscribe()

    async def event_generator():
        try:
            yield "event: connected\ndata: {\"status\": \"connected\"}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            await broadcaster.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

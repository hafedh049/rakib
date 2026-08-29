import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.logging import get_logger
from app.deps import AgentUser
from app.events.types import Event
from app.notifiers.sse import broker

router = APIRouter(prefix="/events", tags=["events"])
log = get_logger(__name__)

#: Comment frames keep proxies from closing an idle connection.
HEARTBEAT_SECONDS = 20


def _frame(event: Event) -> str:
    body = json.dumps(
        {"id": event.id, "name": str(event.name), "at": event.at.isoformat(),
         "payload": event.payload},
        default=str, ensure_ascii=False,
    )
    return f"id: {event.id}\nevent: {event.name}\ndata: {body}\n\n"


@router.get("/stream")
async def stream(request: Request, user: AgentUser) -> StreamingResponse:
    """Role-scoped server-sent events.

    Events carry a minimum role (events/types.EVENT_MIN_ROLE): an agent never
    receives supervisor-only traffic such as triage corrections.
    """
    subscriber = broker.subscribe(
        role=str(user.role),
        department_id=str(user.department_id) if user.department_id else None,
    )

    async def publisher() -> AsyncIterator[str]:
        yield ": connected\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(
                        subscriber.queue.get(), timeout=HEARTBEAT_SECONDS
                    )
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield _frame(event)
        finally:
            broker.unsubscribe(subscriber)
            log.info("sse.disconnected", role=str(user.role))

    return StreamingResponse(
        publisher(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # nginx buffers streamed responses by default, which breaks SSE.
            "X-Accel-Buffering": "no",
        },
    )

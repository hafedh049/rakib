"""Server-sent events fan-out.

Runs inside the API process, because that is where the browser connections are.
Each connected client owns a bounded queue: a slow reader is dropped rather than
allowed to grow memory without limit.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, ClassVar

from app.core.logging import get_logger
from app.events.types import EVENT_MIN_ROLE, Event, EventName
from app.models.user import Role, role_at_least

log = get_logger(__name__)

CLIENT_QUEUE_SIZE = 100


# eq=False keeps identity hashing: subscribers live in a set, and a generated
# __eq__ would null __hash__.
@dataclass(eq=False)
class Subscriber:
    role: str
    department_id: str | None = None
    queue: asyncio.Queue[Event] = field(
        default_factory=lambda: asyncio.Queue(maxsize=CLIENT_QUEUE_SIZE)
    )


class SSEBroker:
    """In-process registry of connected SSE clients."""

    def __init__(self) -> None:
        self._subscribers: set[Subscriber] = set()

    def subscribe(self, role: str, department_id: str | None = None) -> Subscriber:
        subscriber = Subscriber(role=role, department_id=department_id)
        self._subscribers.add(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: Subscriber) -> None:
        self._subscribers.discard(subscriber)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def publish(self, event: Event) -> int:
        """Deliver to every client allowed to see this event. Returns the count."""
        minimum = EVENT_MIN_ROLE.get(event.name, "supervisor")
        delivered = 0
        for subscriber in list(self._subscribers):
            if not role_at_least(subscriber.role, Role(minimum)):
                continue
            try:
                subscriber.queue.put_nowait(event)
                delivered += 1
            except asyncio.QueueFull:
                # A client that cannot keep up is dropped; the UI reconnects and
                # refetches, which is cheaper than unbounded buffering.
                log.warning("sse.client_dropped", role=subscriber.role)
                self.unsubscribe(subscriber)
        return delivered


broker = SSEBroker()


class SSENotifier:
    name: ClassVar[str] = "sse"
    runs_in: ClassVar[str] = "api"

    async def send(self, event: EventName, payload: dict[str, Any]) -> None:
        broker.publish(Event(name=event, payload=payload))

"""Notifier protocol.

Adding a channel is a new class plus one line in `events/subscriptions.py`
(spec 4.4). Notifiers never raise: a failed delivery is logged, not escalated.

`runs_in` splits the two execution contexts. Most notifiers run out-of-band in
the notify worker; the SSE one must run inside the API process because that is
where the browser connections live.
"""

from typing import Any, ClassVar, Protocol, runtime_checkable

from app.events.types import EventName


@runtime_checkable
class Notifier(Protocol):
    name: ClassVar[str]
    runs_in: ClassVar[str]  # "worker" | "api"

    async def send(self, event: EventName, payload: dict[str, Any]) -> None: ...


class LoggingNotifier:
    """Base for channels that are specified but not wired to a provider.

    These ship with the complete interface so enabling them later is a
    configuration change, not a refactor.
    """

    name: ClassVar[str] = "logging"
    runs_in: ClassVar[str] = "worker"

    async def send(self, event: EventName, payload: dict[str, Any]) -> None:
        from app.core.logging import get_logger

        get_logger(f"notifier.{self.name}").info(
            "notifier.stub_delivery",
            channel=self.name,
            event_name=str(event),
            ref=payload.get("ref"),
        )

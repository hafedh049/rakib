"""Resolve an event to its notifiers and fan out.

Shared by the notify worker (out-of-band channels) and the API process (SSE),
which is why the execution context is a parameter rather than an assumption.
"""

from typing import Any

from app.core.logging import get_logger
from app.events.subscriptions import SUBSCRIPTIONS
from app.events.types import EventName

log = get_logger(__name__)


async def dispatch(
    event: EventName, payload: dict[str, Any], runs_in: str = "worker"
) -> int:
    """Deliver one event to every notifier registered for this context.

    A notifier that raises is logged and skipped; one broken channel must never
    stop the others.
    """
    delivered = 0
    for notifier_class in SUBSCRIPTIONS.get(event, []):
        if getattr(notifier_class, "runs_in", "worker") != runs_in:
            continue
        notifier = notifier_class()
        try:
            await notifier.send(event, payload)
            delivered += 1
        except Exception as exc:  # noqa: BLE001 — isolate channel failures
            log.error(
                "notifier.failed",
                channel=getattr(notifier_class, "name", notifier_class.__name__),
                event_name=str(event),
                error=str(exc),
            )
    return delivered

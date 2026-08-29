"""Which notifiers care about which events.

A new channel is a new class plus one line here (spec 4.4).
"""

from app.events.types import EventName
from app.notifiers.base import Notifier
from app.notifiers.email import EmailNotifier
from app.notifiers.sse import SSENotifier

SUBSCRIPTIONS: dict[EventName, list[type[Notifier]]] = {
    EventName.COMPLAINT_CREATED: [EmailNotifier, SSENotifier],
    EventName.COMPLAINT_TRIAGED: [SSENotifier],
    EventName.COMPLAINT_ASSIGNED: [EmailNotifier, SSENotifier],
    EventName.COMPLAINT_UPDATED: [SSENotifier],
    EventName.COMPLAINT_REPLIED: [EmailNotifier, SSENotifier],
    EventName.COMPLAINT_RESOLVED: [EmailNotifier, SSENotifier],
    EventName.TRIAGE_CORRECTED: [SSENotifier],
}

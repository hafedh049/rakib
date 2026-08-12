from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

STREAM_KEY = "events"


class EventName(StrEnum):
    COMPLAINT_CREATED = "complaint.created"
    COMPLAINT_TRIAGED = "complaint.triaged"
    COMPLAINT_ASSIGNED = "complaint.assigned"
    COMPLAINT_UPDATED = "complaint.updated"
    COMPLAINT_REPLIED = "complaint.replied"
    COMPLAINT_RESOLVED = "complaint.resolved"
    SLA_WARNING = "sla.warning"
    SLA_BREACHED = "sla.breached"
    ESCALATED = "complaint.escalated"
    TRIAGE_CORRECTED = "triage.corrected"
    MODEL_PROMOTED = "model.promoted"


@dataclass(frozen=True)
class Event:
    name: EventName
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: uuid4().hex)
    at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_stream(self) -> dict[str, str]:
        """Redis streams store flat string fields, so the payload is JSON."""
        import json

        return {
            "id": self.id,
            "name": str(self.name),
            "at": self.at.isoformat(),
            "payload": json.dumps(self.payload, default=str, ensure_ascii=False),
        }

    @classmethod
    def from_stream(cls, fields: dict[str, str]) -> "Event":
        import json

        return cls(
            id=fields.get("id", uuid4().hex),
            name=EventName(fields["name"]),
            at=datetime.fromisoformat(fields["at"]),
            payload=json.loads(fields.get("payload") or "{}"),
        )


#: Which roles may see an event on the SSE stream. Claimants get nothing: their
#: updates arrive by email and on the tracking page, not on a firehose.
EVENT_MIN_ROLE: dict[EventName, str] = {
    EventName.COMPLAINT_CREATED: "agent",
    EventName.COMPLAINT_TRIAGED: "agent",
    EventName.COMPLAINT_ASSIGNED: "agent",
    EventName.COMPLAINT_UPDATED: "agent",
    EventName.COMPLAINT_REPLIED: "agent",
    EventName.COMPLAINT_RESOLVED: "agent",
    EventName.SLA_WARNING: "agent",
    EventName.SLA_BREACHED: "supervisor",
    EventName.ESCALATED: "supervisor",
    EventName.TRIAGE_CORRECTED: "supervisor",
    EventName.MODEL_PROMOTED: "admin",
}

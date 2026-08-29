from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class Channel(StrEnum):
    WEB = "web"           # formulaire en ligne
    EMAIL = "email"       # saisi par un agent
    AGENCE = "agence"     # depot au guichet
    PHONE = "phone"       # saisi par un agent du centre d'appel
    COURRIER = "courrier"  # courrier postal, saisi par le service


class Status(StrEnum):
    NEW = "new"
    TRIAGED = "triaged"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_CLAIMANT = "pending_claimant"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"


#: Terminal states: no further routing happens.
CLOSED_STATUSES = {Status.RESOLVED, Status.CLOSED, Status.REJECTED}


class TriageState(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"
    MANUAL = "manual"


class AssignmentMethod(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"
    QUEUE = "queue"       # left in the department queue, unassigned


# --------------------------------------------------------------------- embedded parts
class Claimant(BaseModel):
    #: Set when the complaint was filed by a signed-in claimant; anonymous
    #: submissions leave it None and rely on the signed tracking token.
    user_id: PydanticObjectId | None = None
    full_name: str
    email: str | None = None
    phone: str | None = None
    #: Account number, CIN or contract reference — whatever identifies them.
    external_id: str | None = None
    is_vip: bool = False


class Analysis(BaseModel):
    """What the engine decided, and the evidence for it."""

    category: str | None = None
    #: Share of matched evidence held by the winner — an evidence ratio, not a
    #: calibrated probability.
    category_confidence: float | None = None
    category_alternatives: list[tuple[str, float]] = Field(default_factory=list)
    language: str | None = None
    keywords: list[str] = Field(default_factory=list)
    #: The terms that fired, per category. Shown to the agent so a decision can
    #: be argued with rather than merely accepted.
    evidence: dict[str, list[str]] = Field(default_factory=dict)
    needs_human_triage: bool = False
    triage_reason: str | None = None
    engine: str | None = None
    engine_version: str | None = None
    latency_ms: int | None = None
    analyzed_at: datetime | None = None


class Assignment(BaseModel):
    department_id: PydanticObjectId | None = None
    department_code: str | None = None
    agent_id: PydanticObjectId | None = None
    assigned_at: datetime | None = None
    method: AssignmentMethod = AssignmentMethod.AUTO


class Message(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    author_type: Literal["agent", "claimant", "system"]
    author_id: PydanticObjectId | None = None
    author_name: str | None = None
    body: str
    #: Internal notes are never exposed on the public tracking view.
    internal: bool = False


class TimelineEntry(BaseModel):
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor_type: Literal["system", "agent", "user", "engine"]
    actor_id: str | None = None
    action: str
    meta: dict = Field(default_factory=dict)


# ------------------------------------------------------------------------- document
class Complaint(Document):
    ref: str
    channel: Channel = Channel.WEB
    claimant: Claimant
    subject: str
    body: str
    #: Cached output of the normalisation stage; what search runs against.
    normalized_text: str = ""
    analysis: Analysis = Field(default_factory=Analysis)
    assignment: Assignment | None = None
    status: Status = Status.NEW
    triage_state: TriageState = TriageState.PENDING
    messages: list[Message] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    #: A human changed the category or department.
    corrected: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "complaints"
        indexes = [
            pymongo.IndexModel([("ref", 1)], unique=True, name="complaint_ref"),
            pymongo.IndexModel(
                [("assignment.agent_id", 1), ("status", 1)], name="complaint_agent"
            ),
            pymongo.IndexModel(
                [("assignment.department_id", 1), ("status", 1)],
                name="complaint_department",
            ),
            pymongo.IndexModel(
                [("analysis.category", 1), ("created_at", -1)], name="complaint_category"
            ),
            pymongo.IndexModel(
                [("claimant.email", 1), ("created_at", -1)], name="complaint_claimant"
            ),
            pymongo.IndexModel([("triage_state", 1)], name="complaint_triage_state"),
            pymongo.IndexModel([("corrected", 1)], name="complaint_corrected"),
            # Cursor pagination key — must match the sort exactly.
            pymongo.IndexModel(
                [("created_at", -1), ("_id", -1)], name="complaint_cursor"
            ),
            # default_language="none" on purpose: French stemming is useless on
            # Arabic and arabizi, and Mongo allows only ONE text index per
            # collection. normalized_text is included so AR/derja is findable.
            pymongo.IndexModel(
                [("subject", pymongo.TEXT), ("body", pymongo.TEXT),
                 ("normalized_text", pymongo.TEXT)],
                default_language="none",
                name="complaint_text",
            ),
        ]

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    def log(
        self,
        action: str,
        actor_type: Literal["system", "agent", "user", "engine"] = "system",
        actor_id: str | None = None,
        **meta: object,
    ) -> None:
        self.timeline.append(
            TimelineEntry(
                action=action, actor_type=actor_type, actor_id=actor_id, meta=dict(meta)
            )
        )

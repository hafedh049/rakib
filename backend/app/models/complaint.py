from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class Channel(StrEnum):
    """Article 6 requires at minimum an electronic mailbox, an online form and
    in-branch deposit. Everything here maps onto one of the regulator's four
    reception buckets — see app.domain.bct.canal_bct.
    """

    WEB = "web"           # formulaire en ligne
    PHONE = "phone"       # logged by a call-centre agent
    AGENCE = "agence"     # walk-in, logged at the counter or at head office
    EMAIL = "email"       # pasted in by an agent (no inbound ingestion)
    COURRIER = "courrier"  # postal mail, logged by the complaints unit


class Status(StrEnum):
    NEW = "new"
    TRIAGED = "triaged"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_CLAIMANT = "pending_claimant"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"


#: Terminal states: the SLA clock stops and no further routing happens.
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

    # -- Annexe 1 and Annexe 3 of the circulaire ---------------------------
    #: Annexe 3-I. Drives the "repartition par nature de reclamant" table.
    nature: str | None = None
    #: Annexe 1, for legal persons: identifiant au Registre National des
    #: Entreprises.
    identifiant_rne: str | None = None
    #: Annexe 3-II, individuals only. Collected for the annual declaration and
    #: nothing else — never an input to triage, routing or priority.
    genre: str | None = None
    tranche_age: str | None = None


class Reglementaire(BaseModel):
    """What circulaire BCT n°2022-08 requires us to hold beyond the basics.

    Kept in its own block so a regulatory obligation is visibly regulatory, and
    so an audit under Article 12 can be answered by pointing at one field set.
    """

    #: Article 8: the fifteen-working-day clock runs from the acknowledgement,
    #: not from receipt. Stamped when the acknowledgement is actually issued.
    accuse_reception_at: datetime | None = None
    #: Annexe 1: "Investigations menees par l'etablissement".
    investigations_menees: str | None = None
    #: Annexe 1: "Demarches entreprises par l'etablissement pour regler le
    #: probleme".
    demarches_entreprises: str | None = None
    #: Article 8: "motiver toute reponse rejetant en partie ou en totalite les
    #: revendications du client". A rejection without this is a compliance
    #: defect, so the service refuses to record one.
    motivation: str | None = None
    #: Article 2: set when the message is not a reclamation at all (a request
    #: for information, a matter before the courts, an employment dispute...).
    #: Such a message is still handled, but must not inflate the declaration.
    hors_perimetre: str | None = None
    #: Derived from the category so Annexe 3-IV can be produced without
    #: recomputing the mapping over historical rows.
    objet_bct: str | None = None


class Attachment(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    filename: str
    content_type: str
    size: int
    s3_key: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    uploaded_by: PydanticObjectId | None = None


class RuleHit(BaseModel):
    code: str
    label: str
    weight: int
    #: The tokens that actually fired. This is the explainability story — the UI
    #: shows exactly why a complaint became P1. Never omit it (spec 5.4).
    matched: list[str] = Field(default_factory=list)


class Analysis(BaseModel):
    category: str | None = None
    category_confidence: float | None = None
    category_alternatives: list[tuple[str, float]] = Field(default_factory=list)
    subcategory: str | None = None
    priority: int | None = None
    priority_score: int | None = None
    rule_hits: list[RuleHit] = Field(default_factory=list)
    sentiment: Literal["angry", "frustrated", "neutral", "positive"] | None = None
    sentiment_score: float | None = None
    urgency_score: float | None = None
    language: str | None = None
    keywords: list[str] = Field(default_factory=list)
    duplicate_of: PydanticObjectId | None = None
    duplicate_score: float | None = None
    related_ids: list[PydanticObjectId] = Field(default_factory=list)
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


class SLA(BaseModel):
    """Two deadlines, and the earlier one wins.

    `due_at` is the internal target — hours, differentiated by priority, so an
    urgent complaint is chased long before the law requires. `legal_due_at` is
    the Article 8 ceiling in *jours ouvrables* from the acknowledgement. A bank
    may be faster than the regulation; it may never be slower, so the effective
    deadline is min(internal, legal) and `legal_breached` is tracked separately
    because missing the second is a reportable event, not a KPI wobble.
    """

    due_at: datetime | None = None
    hours: int | None = None
    breached: bool = False
    warned: bool = False          # 80% of the budget consumed
    escalation_level: int = 0
    resolved_at: datetime | None = None

    #: Article 8 ceiling. Never later than 15 jours ouvrables after the
    #: acknowledgement, whatever the internal target says.
    legal_due_at: datetime | None = None
    legal_days: int | None = None
    legal_breached: bool = False


class Message(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    author_type: Literal["agent", "claimant", "system"]
    author_id: PydanticObjectId | None = None
    author_name: str | None = None
    body: str
    #: Internal notes are never exposed on the public tracking view.
    internal: bool = False
    attachments: list[Attachment] = Field(default_factory=list)


class TimelineEntry(BaseModel):
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor_type: Literal["system", "agent", "user", "engine"]
    actor_id: str | None = None
    action: str
    meta: dict = Field(default_factory=dict)


class Satisfaction(BaseModel):
    score: int                    # 1..5
    comment: str | None = None
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ------------------------------------------------------------------------- document
class Complaint(Document):
    ref: str
    channel: Channel = Channel.WEB
    claimant: Claimant
    subject: str
    body: str
    #: Cached output of the normalisation stage; feeds dedup and the classifier.
    normalized_text: str = ""
    attachments: list[Attachment] = Field(default_factory=list)
    analysis: Analysis = Field(default_factory=Analysis)
    assignment: Assignment | None = None
    sla: SLA = Field(default_factory=SLA)
    reglementaire: Reglementaire = Field(default_factory=Reglementaire)
    status: Status = Status.NEW
    triage_state: TriageState = TriageState.PENDING
    messages: list[Message] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    satisfaction: Satisfaction | None = None
    #: A human changed the category or department. Feeds the correction rate,
    #: which is one of the key performance indicators Article 9 requires.
    corrected: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "complaints"
        indexes = [
            pymongo.IndexModel([("ref", 1)], unique=True, name="complaint_ref"),
            pymongo.IndexModel(
                [("status", 1), ("sla.due_at", 1)], name="complaint_status_due"
            ),
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

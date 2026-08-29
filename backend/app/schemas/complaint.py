from datetime import datetime
from typing import Literal

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.complaint import (
    Analysis,
    Assignment,
    Channel,
    Claimant,
    Message,
    Status,
    TimelineEntry,
    TriageState,
)
from app.schemas.auth import normalise_tn_phone


class ClaimantIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str | None = None
    phone: str | None = None
    external_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _require_a_way_to_reach_them(self) -> "ClaimantIn":
        """At least one contact channel.

        Many Tunisian claimants give only a phone number, so email is not
        mandatory — but with neither we could never deliver the tracking link
        nor call back, and the complaint would be a dead letter.
        """
        self.phone = normalise_tn_phone(self.phone)
        if not self.email and not self.phone:
            raise ValueError("Un email ou un numero de telephone est obligatoire")
        return self


class ComplaintCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=10_000)
    channel: Channel = Channel.WEB
    claimant: ClaimantIn


class ComplaintCreated(BaseModel):
    """What the portal shows immediately after submission.

    `tracking_url` is displayed once ("conservez ce lien") and emailed when an
    address was given. The ref alone grants nothing.
    """

    id: PydanticObjectId
    ref: str
    status: Status
    tracking_url: str
    created_at: datetime


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)
    internal: bool = False


class ComplaintPatch(BaseModel):
    status: Status | None = None
    category: str | None = None
    department_code: str | None = None
    agent_id: PydanticObjectId | None = None
    is_vip: bool | None = None


class ResolveRequest(BaseModel):
    resolution: str = Field(min_length=1, max_length=10_000)
    notify_claimant: bool = True


class ComplaintListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    ref: str
    subject: str
    channel: Channel
    status: Status
    triage_state: TriageState
    claimant: Claimant
    analysis: Analysis
    assignment: Assignment | None = None
    created_at: datetime
    updated_at: datetime


class ComplaintOut(BaseModel):
    """Full staff view — includes internal notes and the complete analysis."""

    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    ref: str
    channel: Channel
    claimant: Claimant
    subject: str
    body: str
    normalized_text: str
    analysis: Analysis
    assignment: Assignment | None
    status: Status
    triage_state: TriageState
    messages: list[Message]
    timeline: list[TimelineEntry]
    corrected: bool
    created_at: datetime
    updated_at: datetime


class PublicMessage(BaseModel):
    at: datetime
    author_type: Literal["agent", "claimant", "system"]
    author_name: str | None = None
    body: str


class ComplaintPublicOut(BaseModel):
    """What a token-bearing claimant sees. Deliberately narrow.

    No internal notes, no agent identities, no triage internals — a tracking
    link is not a window into the bank's own handling of the file.
    """

    ref: str
    subject: str
    body: str
    status: Status
    channel: Channel
    department: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[PublicMessage]

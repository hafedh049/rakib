"""Contracts between the application and the intelligence layer.

Nothing in `intelligence/` imports from `api/` or `models/`. These plain
dataclasses cross the boundary in both directions, so every engine can be unit
tested with no database and no FastAPI.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar, Protocol


@dataclass(frozen=True)
class DepartmentInfo:
    code: str
    name: str
    keywords: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DedupCandidate:
    id: str
    subject: str
    normalized_text: str
    created_at: datetime
    claimant_email: str | None = None


@dataclass(frozen=True)
class RuleHitDTO:
    code: str
    label: str
    weight: int
    #: The tokens that actually fired — the explainability payload (spec 5.4).
    matched: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TriageInput:
    subject: str
    body: str
    channel: str = "web"
    claimant_email: str | None = None
    claimant_is_vip: bool = False
    claimant_prior_count_30d: int = 0
    claimant_prior_open: int = 0
    attachment_count: int = 0
    departments: list[DepartmentInfo] = field(default_factory=list)
    recent_complaints: list[DedupCandidate] = field(default_factory=list)


@dataclass(frozen=True)
class TriageOutput:
    category: str | None
    category_confidence: float
    category_alternatives: list[tuple[str, float]]
    subcategory: str | None
    department_code: str
    priority: int
    priority_score: int
    rule_hits: list[RuleHitDTO]
    sentiment: str
    sentiment_score: float
    urgency_score: float
    language: str
    keywords: list[str]
    normalized_text: str
    duplicate_of_id: str | None = None
    duplicate_score: float | None = None
    related_ids: list[str] = field(default_factory=list)
    needs_human_triage: bool = False
    triage_reason: str | None = None
    engine: str = "rules"
    model_version: str = "none"
    latency_ms: int = 0
    stages: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class EngineHealth:
    name: str
    ready: bool
    degraded: bool
    model_loaded: bool
    model_version: str | None = None
    detail: str | None = None


class TriageEngine(Protocol):
    name: ClassVar[str]

    async def analyze(self, data: TriageInput) -> TriageOutput: ...

    def health(self) -> EngineHealth: ...


@dataclass(frozen=True)
class Draft:
    text: str
    source_article_id: str
    score: float
    filled_slots: dict[str, str]


@dataclass(frozen=True)
class SuggestionOutput:
    drafts: list[Draft]
    cited_articles: list[str]
    missing_slots: list[str]

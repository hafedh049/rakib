"""Contracts between the application and the intelligence layer.

Nothing in `intelligence/` imports from `api/` or `models/`. These plain
dataclasses cross the boundary in both directions, so the engine can be unit
tested with no database and no FastAPI.
"""

from dataclasses import dataclass, field
from typing import ClassVar, Protocol


@dataclass(frozen=True)
class DepartmentInfo:
    code: str
    name: str
    keywords: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TriageInput:
    subject: str
    body: str
    channel: str = "web"
    claimant_email: str | None = None
    departments: list[DepartmentInfo] = field(default_factory=list)


@dataclass(frozen=True)
class TriageOutput:
    """What the engine decides: a category, a department, and its evidence."""

    category: str | None
    #: Share of the matched evidence held by the winning category. An evidence
    #: ratio, NOT a calibrated probability — it does not claim to be one.
    category_confidence: float
    category_alternatives: list[tuple[str, float]]
    department_code: str
    language: str
    keywords: list[str]
    normalized_text: str
    #: True when the lexicon declined to decide. The complaint is still routed
    #: and still handled; an agent sets the category.
    needs_human_triage: bool
    #: Which threshold the evidence failed, when it did.
    triage_reason: str | None
    engine: str
    engine_version: str
    latency_ms: int
    #: Per-stage timings, surfaced in the analysis view so a decision can be
    #: followed rather than trusted.
    stages: list[dict] = field(default_factory=list)
    #: The terms that fired, per category — the explainability payload.
    evidence: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class EngineHealth:
    name: str
    ready: bool
    degraded: bool
    engine_version: str
    detail: str


class TriageEngine(Protocol):
    """The seam. Swapping the categoriser touches an implementation, not a caller."""

    name: ClassVar[str]

    async def analyze(self, data: TriageInput) -> TriageOutput: ...

    def health(self) -> EngineHealth: ...

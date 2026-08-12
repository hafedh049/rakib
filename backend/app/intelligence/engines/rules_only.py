"""Cold-start engine: no trained model required.

Routes by keyword overlap between the complaint and each department's keyword
set, weighted by IDF so a term shared by every department ("ligne") counts for
far less than a discriminating one ("portabilite").

Category is left unset on purpose. This engine can say which team should look at
a complaint, but it cannot honestly claim a category, so it reports
`category_confidence = 0.0` and `needs_human_triage = True` and offers the
department's categories as one-click alternatives (spec 5.3, cold start).
"""

import math
import time
from typing import ClassVar

from app.core.logging import get_logger
from app.domain.taxonomy import GENERAL_DEPARTMENT_CODE
from app.intelligence.ports import (
    EngineHealth,
    TriageInput,
    TriageOutput,
)
from app.intelligence.rules.engine import (
    TOKEN_RE,
    RuleContext,
    RuleSpec,
    evaluate,
    find_terms,
)
from app.intelligence.rules.subcategory import detect_subcategory
from app.intelligence.text import language as lid
from app.intelligence.text.normalize import normalize

log = get_logger(__name__)

TOP_KEYWORDS = 8


class RulesOnlyTriageEngine:
    """The engine the system falls back to when `ml_artifacts/` is empty."""

    name: ClassVar[str] = "rules"

    def __init__(self, rules: list[RuleSpec] | None = None) -> None:
        self._rules = rules or []

    def set_rules(self, rules: list[RuleSpec]) -> None:
        self._rules = rules

    async def analyze(self, data: TriageInput) -> TriageOutput:
        started = time.perf_counter()
        stages: list[dict] = []

        normalized = normalize(
            data.subject, data.body, has_attachment=data.attachment_count > 0
        )
        stages.append(_stage("normalize", started, chars=len(normalized.text)))

        mark = time.perf_counter()
        detected = lid.detect(normalized)
        stages.append(_stage("language", mark, code=detected.code,
                             source=detected.source))

        mark = time.perf_counter()
        department_code, alternatives = route_by_keywords(
            normalized.indexable, data.departments
        )
        stages.append(_stage("route", mark, department=department_code))

        mark = time.perf_counter()
        context = RuleContext(
            text=normalized.text,
            transliterated=normalized.transliterated,
            features=normalized.features,
            language=detected.code,
            category=None,
            channel=data.channel,
            claimant_is_vip=data.claimant_is_vip,
            prior_count_30d=data.claimant_prior_count_30d,
            prior_open=data.claimant_prior_open,
            attachment_count=data.attachment_count,
        )
        result = evaluate(self._rules, context)
        stages.append(_stage("rules", mark, score=result.priority_score,
                             hits=len(result.hits)))

        latency_ms = int((time.perf_counter() - started) * 1000)
        return TriageOutput(
            category=None,
            category_confidence=0.0,
            category_alternatives=alternatives,
            subcategory=detect_subcategory(None, normalized.indexable),
            department_code=department_code,
            priority=result.priority,
            priority_score=result.priority_score,
            rule_hits=result.hits,
            sentiment=result.sentiment,
            sentiment_score=result.sentiment_score,
            urgency_score=result.urgency_score,
            language=detected.code,
            keywords=top_keywords(normalized.indexable),
            normalized_text=normalized.indexable,
            needs_human_triage=True,
            triage_reason="no_model",
            engine=self.name,
            model_version="rules-v1",
            latency_ms=latency_ms,
            stages=stages,
        )

    def health(self) -> EngineHealth:
        return EngineHealth(
            name=self.name,
            ready=True,
            degraded=True,
            model_loaded=False,
            model_version="rules-v1",
            detail=(
                "Aucun modele entraine: routage par mots-cles, categorisation "
                "laissee a un agent."
            ),
        )


# --------------------------------------------------------------------------- routing
def route_by_keywords(
    text: str, departments: list
) -> tuple[str, list[tuple[str, float]]]:
    """IDF-weighted keyword overlap. Returns (department_code, alternatives)."""
    routable = [d for d in departments if d.keywords]
    if not routable:
        return GENERAL_DEPARTMENT_CODE, []

    document_frequency: dict[str, int] = {}
    for department in routable:
        for keyword in {k.lower() for k in department.keywords}:
            document_frequency[keyword] = document_frequency.get(keyword, 0) + 1

    total = len(routable)
    scores: list[tuple[str, float, list[str]]] = []
    for department in routable:
        matched = find_terms(text, department.keywords)
        score = sum(
            math.log(total / document_frequency.get(term.lower(), 1)) + 1.0
            for term in matched
        )
        scores.append((department.code, score, matched))

    scores.sort(key=lambda row: row[1], reverse=True)
    best_code, best_score, _ = scores[0]
    if best_score <= 0:
        return GENERAL_DEPARTMENT_CODE, []

    winner = next(d for d in routable if d.code == best_code)
    # The winning department's categories, offered as one-click corrections.
    alternatives = [(category, 0.0) for category in winner.categories]
    return best_code, alternatives


def top_keywords(text: str, limit: int = TOP_KEYWORDS) -> list[str]:
    """Frequency-ranked content words — a cheap stand-in until TF-IDF exists."""
    counts: dict[str, int] = {}
    for token in TOKEN_RE.findall(text):
        if len(token) < 4 or token.startswith("<"):
            continue
        counts[token] = counts.get(token, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:limit]]


def _stage(name: str, since: float, **summary: object) -> dict:
    return {
        "name": name,
        "latency_ms": round((time.perf_counter() - since) * 1000, 2),
        "output_summary": summary,
    }

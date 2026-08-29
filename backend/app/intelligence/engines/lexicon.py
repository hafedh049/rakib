"""The engine: deterministic categorisation, then department routing.

Three stages — normalise, identify the language, categorise — followed by a
routing decision. No model is loaded and no network call is made, so the same
complaint always yields the same category and every decision traces back to a
term an administrator can read.

Routing follows the category when the lexicon reaches a verdict, and falls back
to IDF-weighted department keyword overlap when it does not. A complaint the
lexicon cannot categorise therefore still reaches the right desk.
"""

import math
import time
from typing import ClassVar

from app.core.logging import get_logger
from app.domain.taxonomy import GENERAL_DEPARTMENT_CODE, department_for_category
from app.intelligence.lexicon.classifier import classify
from app.intelligence.lexicon.terms import CATEGORY_LEXICON
from app.intelligence.ports import (
    DepartmentInfo,
    EngineHealth,
    TriageInput,
    TriageOutput,
)
from app.intelligence.text import language as lid
from app.intelligence.text.matching import TOKEN_RE, find_terms
from app.intelligence.text.normalize import normalize

log = get_logger(__name__)

ENGINE_VERSION = "lexicon-v1"
TERM_COUNT = sum(len(terms) for terms in CATEGORY_LEXICON.values())
TOP_KEYWORDS = 8


class LexiconTriageEngine:
    """Weighted-lexicon categorisation and keyword routing."""

    name: ClassVar[str] = "lexicon"

    async def analyze(self, data: TriageInput) -> TriageOutput:
        started = time.perf_counter()
        stages: list[dict] = []

        normalized = normalize(data.subject, data.body)
        stages.append(_stage("normalize", started, chars=len(normalized.text)))

        mark = time.perf_counter()
        detected = lid.detect(normalized)
        stages.append(
            _stage("language", mark, code=detected.code, source=detected.source)
        )

        mark = time.perf_counter()
        verdict = classify(normalized.indexable)
        stages.append(
            _stage(
                "classify",
                mark,
                category=verdict.category,
                share=verdict.confidence,
                reason=verdict.reason,
            )
        )

        # The category decides the department; keywords decide it when the
        # lexicon abstained, so an uncategorised complaint still lands somewhere.
        mark = time.perf_counter()
        if verdict.category:
            department_code = department_for_category(verdict.category)
            alternatives = verdict.alternatives
        else:
            department_code, alternatives = route_by_keywords(
                normalized.indexable, data.departments
            )
            alternatives = alternatives or verdict.alternatives
        stages.append(_stage("route", mark, department=department_code))

        return TriageOutput(
            category=verdict.category,
            category_confidence=verdict.confidence,
            category_alternatives=alternatives,
            department_code=department_code,
            language=detected.code,
            keywords=top_keywords(normalized.indexable),
            normalized_text=normalized.indexable,
            needs_human_triage=verdict.category is None,
            triage_reason=None if verdict.category else verdict.reason,
            engine=self.name,
            engine_version=ENGINE_VERSION,
            latency_ms=int((time.perf_counter() - started) * 1000),
            stages=stages,
            evidence=verdict.evidence,
        )

    def health(self) -> EngineHealth:
        return EngineHealth(
            name=self.name,
            ready=True,
            degraded=False,
            engine_version=ENGINE_VERSION,
            detail=(
                f"Categorisation deterministe par lexique pondere "
                f"({TERM_COUNT} termes). Aucun modele, aucun artefact."
            ),
        )


# --------------------------------------------------------------------- routing
def route_by_keywords(
    text: str, departments: list[DepartmentInfo]
) -> tuple[str, list[tuple[str, float]]]:
    """IDF-weighted keyword overlap. Returns (department_code, alternatives).

    A keyword every department claims ("operation") must not decide the routing,
    so each match is discounted by how many departments share it.
    """
    routable = [d for d in departments if d.keywords]
    if not routable:
        return GENERAL_DEPARTMENT_CODE, []

    document_frequency: dict[str, int] = {}
    for department in routable:
        for keyword in {k.lower() for k in department.keywords}:
            document_frequency[keyword] = document_frequency.get(keyword, 0) + 1

    total = len(routable)
    scores: list[tuple[str, float]] = []
    for department in routable:
        matched = find_terms(text, department.keywords)
        score = sum(
            math.log(total / document_frequency.get(term.lower(), 1)) + 1.0
            for term in matched
        )
        scores.append((department.code, score))

    scores.sort(key=lambda row: row[1], reverse=True)
    best_code, best_score = scores[0]
    if best_score <= 0:
        return GENERAL_DEPARTMENT_CODE, []

    winner = next(d for d in routable if d.code == best_code)
    # The winning department's categories, offered as one-click corrections.
    return best_code, [(category, 0.0) for category in winner.categories]


def top_keywords(text: str, limit: int = TOP_KEYWORDS) -> list[str]:
    """Frequency-ranked content words, shown beside the analysis."""
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

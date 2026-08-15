"""The production engine: deterministic and explainable.

Same six stages as before — normalise, language, classify, rules, dedup, decide
— but the classify stage is a weighted lexicon rather than a learned model. The
port above it is unchanged, which is the point: swapping the brain touched this
file and the factory in deps.py, nothing else.

Routing follows the category when the lexicon reaches a verdict, and falls back
to IDF-weighted department keyword overlap when it does not. So a complaint the
lexicon cannot categorise still reaches the right team.
"""

import time
from typing import ClassVar

from app.core.logging import get_logger
from app.domain.taxonomy import department_for_category
from app.intelligence.engines.rules_only import (
    _stage,
    route_by_keywords,
    top_keywords,
)
from app.intelligence.lexicon.classifier import classify
from app.intelligence.lexicon.terms import CATEGORY_LEXICON
from app.intelligence.ports import EngineHealth, TriageInput, TriageOutput
from app.intelligence.rules.engine import RuleContext, RuleSpec, evaluate
from app.intelligence.rules.subcategory import detect_subcategory
from app.intelligence.text import language as lid
from app.intelligence.text.normalize import normalize

log = get_logger(__name__)

LEXICON_VERSION = "lexicon-v1"
TERM_COUNT = sum(len(terms) for terms in CATEGORY_LEXICON.values())


class LexiconTriageEngine:
    """Weighted-lexicon categorisation plus the deterministic rule set."""

    name: ClassVar[str] = "lexicon"

    def __init__(self, rules: list[RuleSpec] | None = None) -> None:
        self._rules = rules or []

    def set_rules(self, rules: list[RuleSpec]) -> None:
        self._rules = rules

    def reload(self) -> bool:
        """Nothing to reload — there is no artifact. Kept for port parity."""
        return True

    async def analyze(self, data: TriageInput) -> TriageOutput:
        started = time.perf_counter()
        stages: list[dict] = []

        normalized = normalize(
            data.subject, data.body, has_attachment=data.attachment_count > 0
        )
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

        # Category decides the department; keywords decide it when the lexicon
        # abstained, so an uncategorised complaint still lands on a real desk.
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

        mark = time.perf_counter()
        context = RuleContext(
            text=normalized.text,
            transliterated=normalized.transliterated,
            features=normalized.features,
            language=detected.code,
            category=verdict.category,
            channel=data.channel,
            claimant_is_vip=data.claimant_is_vip,
            prior_count_30d=data.claimant_prior_count_30d,
            prior_open=data.claimant_prior_open,
            attachment_count=data.attachment_count,
        )
        result = evaluate(self._rules, context)
        stages.append(
            _stage("rules", mark, score=result.priority_score, hits=len(result.hits))
        )

        latency_ms = int((time.perf_counter() - started) * 1000)
        return TriageOutput(
            category=verdict.category,
            category_confidence=verdict.confidence,
            category_alternatives=alternatives,
            subcategory=detect_subcategory(verdict.category, normalized.indexable),
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
            needs_human_triage=verdict.category is None,
            triage_reason=None if verdict.category else verdict.reason,
            engine=self.name,
            engine_version=LEXICON_VERSION,
            latency_ms=latency_ms,
            stages=stages,
        )

    def health(self) -> EngineHealth:
        return EngineHealth(
            name=self.name,
            ready=True,
            # Not degraded: this is the intended engine, not a fallback. There is
            # no model to be missing, so there is no degraded state to report.
            degraded=False,
            engine_version=LEXICON_VERSION,
            detail=(
                f"Categorisation deterministe par lexique pondere "
                f"({TERM_COUNT} termes), editable depuis la console."
            ),
        )

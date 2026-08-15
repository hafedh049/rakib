"""Deterministic category assignment.

Scores every category by the weighted terms it matches, discounts terms that
several categories share, and declares a winner only when it clears the runner-up
by a margin. Below that margin the classifier says so rather than guessing —
the same contract the trained model had, honoured by different means.

Two properties a trained classifier could not offer, and which matter more in a
bank than a few points of accuracy:

*   **Traceability.** The verdict carries the exact terms that produced it, so
    an agent — or an auditor under Article 12 — can see why, not just what.
*   **Determinism.** The same complaint always yields the same category. There
    is no model version to reconcile, no drift, and no retraining to justify.

What it gives up is generalisation: a complaint phrased entirely outside the
lexicon scores zero and goes to a human. That is a real cost and it is measured
in scripts/evaluate.py against the same gold and wild sets the trained model
was held to.
"""

import math
from dataclasses import dataclass, field

from app.intelligence.lexicon.terms import CATEGORY_LEXICON
from app.intelligence.rules.engine import find_terms

#: A winner must hold at least this share of the total evidence, otherwise the
#: complaint is ambiguous. 0.40 lets a clear winner through against two weak
#: rivals while stopping a near-tie.
MIN_EVIDENCE_SHARE = 0.40

#: ...and must beat the runner-up outright by this ratio.
MIN_MARGIN_RATIO = 1.30

#: Below this raw score there is simply not enough evidence to act on, whatever
#: the shares look like. One supporting term alone must never decide.
MIN_SCORE = 2.0


@dataclass(frozen=True)
class LexiconVerdict:
    category: str | None
    #: Share of total matched evidence held by the winner. This is an evidence
    #: ratio, NOT a probability — it is not calibrated and does not claim to be.
    confidence: float
    alternatives: list[tuple[str, float]] = field(default_factory=list)
    #: The terms that fired, per category. The explainability payload.
    evidence: dict[str, list[str]] = field(default_factory=dict)
    reason: str = ""


def _inverse_category_frequency() -> dict[str, float]:
    """Discount terms that several categories claim.

    "deux fois" appears under cards, ATMs, payments and credit alike; "chequier"
    appears once. Without this, the common term drowns the discriminating one —
    the same failure the department router already guards against.
    """
    occurrences: dict[str, int] = {}
    for terms in CATEGORY_LEXICON.values():
        for term in terms:
            occurrences[term] = occurrences.get(term, 0) + 1

    total = len(CATEGORY_LEXICON) or 1
    return {
        term: math.log(total / count) + 1.0 for term, count in occurrences.items()
    }


#: Computed once — the lexicon does not change at runtime.
ICF: dict[str, float] = _inverse_category_frequency()


def classify(indexable: str) -> LexiconVerdict:
    """Assign a category, or admit there isn't one."""
    scores: dict[str, float] = {}
    evidence: dict[str, list[str]] = {}

    for category, terms in CATEGORY_LEXICON.items():
        matched = find_terms(indexable, list(terms))
        if not matched:
            continue
        evidence[category] = matched
        scores[category] = sum(
            terms[term.lower()] * ICF.get(term.lower(), 1.0) for term in matched
        )

    if not scores:
        return LexiconVerdict(None, 0.0, [], {}, "no_signal")

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    total = sum(scores.values())
    best_category, best_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0

    share = best_score / total if total else 0.0
    alternatives = [
        (category, round(score / total, 3)) for category, score in ranked[:4]
    ]

    if best_score < MIN_SCORE:
        return LexiconVerdict(
            None, round(share, 3), alternatives, evidence, "insufficient_evidence"
        )
    if share < MIN_EVIDENCE_SHARE:
        return LexiconVerdict(
            None, round(share, 3), alternatives, evidence, "evidence_too_spread"
        )
    if runner_up and best_score < runner_up * MIN_MARGIN_RATIO:
        return LexiconVerdict(
            None, round(share, 3), alternatives, evidence, "margin_too_narrow"
        )

    return LexiconVerdict(
        best_category, round(share, 3), alternatives, evidence, "lexicon"
    )

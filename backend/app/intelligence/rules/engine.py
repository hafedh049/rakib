"""Weighted rule evaluation: priority, sentiment, urgency.

Every rule that fires records the tokens that made it fire. That list is what
the UI shows next to the priority badge, and it is why a supervisor can argue
with the system instead of just trusting it (spec 5.4).
"""

import re
from dataclasses import dataclass, field
from typing import Any

from app.intelligence.ports import RuleHitDTO
from app.intelligence.rules.lexicons import (
    ALL_NEGATIONS,
    NEGATION_WINDOW,
    NEGATIVE_TERMS,
    POSITIVE_TERMS,
)
from app.intelligence.text.normalize import TextFeatures

# Priority buckets (spec 5.4).
PRIORITY_THRESHOLDS = ((70, 1), (45, 2), (20, 3))
DEFAULT_PRIORITY = 4

#: Every complaint starts at "normale" and rules move it from there. Without a
#: base, a perfectly ordinary complaint with no urgency markers scores near zero
#: and lands in "basse" — which would put the bulk of real traffic in the bucket
#: nobody watches. Rules with negative weights can still push it down.
BASE_SCORE = 20

SENTIMENT_BUCKETS = ((-0.50, "angry"), (-0.15, "frustrated"), (0.25, "neutral"))
DEFAULT_SENTIMENT = "positive"
MIN_SENTIMENT_DENOMINATOR = 3

TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)


@dataclass(frozen=True)
class RuleSpec:
    """A rule, decoupled from its Mongo representation."""

    code: str
    label: str
    kind: str
    weight: int
    config: dict[str, Any] = field(default_factory=dict)
    active: bool = True
    order: int = 100


@dataclass(frozen=True)
class RuleContext:
    text: str
    transliterated: str = ""
    features: TextFeatures | None = None
    language: str = "fr"
    category: str | None = None
    channel: str = "web"
    claimant_is_vip: bool = False
    prior_count_30d: int = 0
    prior_open: int = 0
    attachment_count: int = 0

    @property
    def searchable(self) -> str:
        return f"{self.text} {self.transliterated}".strip()


@dataclass(frozen=True)
class RulesResult:
    priority: int
    priority_score: int
    hits: list[RuleHitDTO]
    sentiment: str
    sentiment_score: float
    urgency_score: float


# --------------------------------------------------------------------------- matching
def find_terms(text: str, terms: list[str]) -> list[str]:
    """Return the terms present in `text`.

    Multi-word terms are matched as substrings; single words are matched against
    the token set so "pas" does not fire inside "passer".
    """
    tokens = set(TOKEN_RE.findall(text))
    matched: list[str] = []
    for term in terms:
        needle = term.strip().lower()
        if not needle:
            continue
        if " " in needle:
            if needle in text:
                matched.append(term)
        elif needle in tokens:
            matched.append(term)
    return matched


def _compare(left: Any, op: str, right: Any) -> bool:
    try:
        match op:
            case "eq":
                return bool(left == right)
            case "ne":
                return bool(left != right)
            case "gt":
                return bool(left > right)
            case "gte":
                return bool(left >= right)
            case "lt":
                return bool(left < right)
            case "lte":
                return bool(left <= right)
            case "in":
                return left in right
            case _:
                return False
    except TypeError:
        return False


def _field_value(context: RuleContext, path: str) -> Any:
    """Resolve the small, explicit set of paths a field rule may address."""
    features = context.features
    return {
        "claimant_is_vip": context.claimant_is_vip,
        "attachment_count": context.attachment_count,
        "channel": context.channel,
        "language": context.language,
        "category": context.category,
        "prior_count_30d": context.prior_count_30d,
        "prior_open": context.prior_open,
        "uppercase_ratio": features.uppercase_ratio if features else 0.0,
        "exclamation_count": features.exclamation_count if features else 0,
        "question_count": features.question_count if features else 0,
        "word_count": features.word_count if features else 0,
        "char_count": features.char_count if features else 0,
        "digit_ratio": features.digit_ratio if features else 0.0,
    }.get(path)


# ------------------------------------------------------------------ rule evaluation
def evaluate_rule(rule: RuleSpec, context: RuleContext) -> RuleHitDTO | None:
    """Evaluate one rule. Returns a hit with its matched tokens, or None."""
    if not rule.active:
        return None
    config = rule.config
    text = context.searchable

    match rule.kind:
        case "lexicon":
            matched = find_terms(text, config.get("terms", []))
            if not matched:
                return None
            cap = int(config.get("cap", 1))
            multiplier = min(len(matched), max(cap, 1))
            return RuleHitDTO(
                code=rule.code, label=rule.label,
                weight=rule.weight * multiplier, matched=matched[:10],
            )

        case "regex":
            flags = re.IGNORECASE if "i" in str(config.get("flags", "")) else 0
            try:
                pattern = re.compile(config.get("pattern", ""), flags)
            except re.error:
                return None
            found = pattern.findall(text)
            if not found:
                return None
            matched = [m if isinstance(m, str) else " ".join(m) for m in found[:5]]
            return RuleHitDTO(
                code=rule.code, label=rule.label, weight=rule.weight, matched=matched
            )

        case "field":
            value = _field_value(context, config.get("path", ""))
            if value is None or not _compare(value, config.get("op", "eq"),
                                             config.get("value")):
                return None
            return RuleHitDTO(
                code=rule.code, label=rule.label, weight=rule.weight,
                matched=[f"{config.get('path')}={value}"],
            )

        case "history":
            source = config.get("source", "prior_count_30d")
            count = (
                context.prior_count_30d
                if source == "prior_count_30d"
                else context.prior_open
            )
            if count < int(config.get("min_count", 1)):
                return None
            return RuleHitDTO(
                code=rule.code, label=rule.label, weight=rule.weight,
                matched=[f"{source}={count}"],
            )

        case "length":
            length = len(context.text)
            minimum, maximum = config.get("min"), config.get("max")
            if minimum is not None and length < int(minimum):
                return None
            if maximum is not None and length > int(maximum):
                return None
            if minimum is None and maximum is None:
                return None
            return RuleHitDTO(
                code=rule.code, label=rule.label, weight=rule.weight,
                matched=[f"longueur={length}"],
            )

        case "category_weight":
            if context.category is None:
                return None
            weight = config.get("map", {}).get(context.category)
            if not weight:
                return None
            return RuleHitDTO(
                code=rule.code, label=rule.label, weight=int(weight),
                matched=[context.category],
            )

    return None


def evaluate(rules: list[RuleSpec], context: RuleContext) -> RulesResult:
    hits = [
        hit
        for hit in (evaluate_rule(rule, context) for rule in sorted(rules, key=lambda r: r.order))
        if hit is not None
    ]
    score = max(0, BASE_SCORE + sum(hit.weight for hit in hits))
    sentiment, sentiment_score = analyse_sentiment(context)

    return RulesResult(
        priority=bucket_priority(score),
        priority_score=score,
        hits=hits,
        sentiment=sentiment,
        sentiment_score=sentiment_score,
        urgency_score=min(1.0, score / 100),
    )


def bucket_priority(score: int) -> int:
    for threshold, priority in PRIORITY_THRESHOLDS:
        if score >= threshold:
            return priority
    return DEFAULT_PRIORITY


# -------------------------------------------------------------------------- sentiment
def analyse_sentiment(context: RuleContext) -> tuple[str, float]:
    """Lexicon polarity with a negation window, plus punctuation and caps.

    No model: a negation-aware lexicon agrees with human labels often enough to
    drive prioritisation, and it stays explainable (spec 5.4).
    """
    text = context.searchable
    tokens = TOKEN_RE.findall(text)
    polarity = 0.0
    counted = 0

    for index, token in enumerate(tokens):
        value = 1.0 if token in POSITIVE_TERMS else -1.0 if token in NEGATIVE_TERMS else 0.0
        if value == 0.0:
            continue
        window = tokens[max(0, index - NEGATION_WINDOW):index]
        if any(previous in ALL_NEGATIONS for previous in window):
            value = -value
        polarity += value
        counted += 1

    # Multi-word terms are missed by the token loop; catch them as substrings.
    for term in POSITIVE_TERMS | NEGATIVE_TERMS:
        if " " in term and term in text:
            polarity += 1.0 if term in POSITIVE_TERMS else -1.0
            counted += 1

    # Divide by at least 3 so a single negative word ("probleme") reads as mild
    # frustration rather than pinning the scale to "angry".
    score = polarity / max(counted, MIN_SENTIMENT_DENOMINATOR) if counted else 0.0

    if context.features is not None:
        if context.features.uppercase_ratio >= 0.4:
            score -= 0.3
        if context.features.exclamation_count >= 3:
            score -= 0.2
        if context.features.repeated_char_runs >= 2:
            score -= 0.1

    score = max(-1.0, min(1.0, score))
    return bucket_sentiment(score), round(score, 3)


def bucket_sentiment(score: float) -> str:
    for threshold, label in SENTIMENT_BUCKETS:
        if score < threshold:
            return label
    return DEFAULT_SENTIMENT

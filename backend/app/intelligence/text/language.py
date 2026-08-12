"""Language identification: fr | ar | ar-tn | en | other.

fastText's `lid.176.ftz` (917 KB) does the heavy lifting, but the module is built
to work without it: if the artifact is missing the system must still boot and
classify (spec section 11), so a script-and-stopword heuristic takes over.

`ar-tn` is not a fastText label. Tunisian derja written in Latin script is
detected here, because fastText will happily call "3andi mochkla fel internet"
Romanian.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.text.normalize import NormalizedText

log = get_logger(__name__)

LID_MODEL_FILENAME = "lid.176.ftz"
SUPPORTED = {"fr", "ar", "en"}

#: Above this share of arabizi tokens the text is Tunisian derja regardless of
#: what fastText thinks (spec 5.2).
ARABIZI_TOKEN_THRESHOLD = 0.15
#: Below this fastText confidence we do not trust a Latin-script verdict.
LOW_CONFIDENCE = 0.60
ARABIC_SCRIPT_THRESHOLD = 0.50

FRENCH_MARKERS = {
    "je", "vous", "nous", "le", "la", "les", "des", "une", "est", "pas", "mon",
    "ma", "mes", "pour", "avec", "depuis", "toujours", "facture", "merci",
    "bonjour", "cordialement", "reseau", "ligne", "probleme", "demande",
}
ENGLISH_MARKERS = {
    "the", "and", "you", "your", "for", "with", "since", "please", "still",
    "issue", "problem", "network", "bill", "account", "service", "thanks",
}


@dataclass(frozen=True)
class LanguageResult:
    code: str
    confidence: float
    #: "fasttext" | "script" | "arabizi" | "heuristic" — surfaced in the trace so
    #: a degraded run is visible rather than silent.
    source: str


@lru_cache(maxsize=1)
def _load_model() -> Any | None:
    path = os.path.join(settings.ml_artifacts_dir, LID_MODEL_FILENAME)
    if not os.path.exists(path):
        log.warning("lid.model_missing", path=path)
        return None
    try:
        import fasttext

        # fastText prints a deprecation banner to stderr on load; harmless.
        return fasttext.load_model(path)
    except Exception as exc:
        log.error("lid.load_failed", path=path, error=str(exc))
        return None


def model_available() -> bool:
    return _load_model() is not None


def detect(normalized: NormalizedText) -> LanguageResult:
    features = normalized.features

    # Arabic script is unambiguous — no model needed.
    if features.arabic_ratio >= ARABIC_SCRIPT_THRESHOLD:
        return LanguageResult("ar", min(1.0, features.arabic_ratio), "script")

    verdict = _fasttext_verdict(normalized.text) or _heuristic_verdict(normalized.text)

    # Latin-script derja: fastText has no label for it, so we own this decision.
    if (
        features.arabizi_token_ratio >= ARABIZI_TOKEN_THRESHOLD
        and verdict.code in {"fr", "en", "other"}
        and verdict.confidence < LOW_CONFIDENCE
    ):
        return LanguageResult("ar-tn", features.arabizi_token_ratio, "arabizi")

    return verdict


def _fasttext_verdict(text: str) -> LanguageResult | None:
    model = _load_model()
    if model is None or not text.strip():
        return None
    try:
        labels, scores = model.predict(text.replace("\n", " "), k=1)
    except Exception as exc:
        log.warning("lid.predict_failed", error=str(exc))
        return None
    code = labels[0].replace("__label__", "")
    confidence = float(scores[0])
    return LanguageResult(
        code if code in SUPPORTED else "other", confidence, "fasttext"
    )


def _heuristic_verdict(text: str) -> LanguageResult:
    """Stopword fallback for when the artifact is absent."""
    tokens = set(text.split())
    french = len(tokens & FRENCH_MARKERS)
    english = len(tokens & ENGLISH_MARKERS)

    if french == 0 and english == 0:
        return LanguageResult("other", 0.0, "heuristic")
    if french >= english:
        return LanguageResult("fr", french / (french + english), "heuristic")
    return LanguageResult("en", english / (french + english), "heuristic")

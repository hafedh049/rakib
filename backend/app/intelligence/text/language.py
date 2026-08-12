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

#: Above this share of derja markers the text is Tunisian, whatever fastText says.
DERJA_THRESHOLD = 0.15
ARABIC_SCRIPT_THRESHOLD = 0.50

#: Latin-script derja that carries no digit substitution. The arabizi pattern
#: alone catches "3andi" and "7atta" but misses "el fatoura mte3i hedha chhar",
#: which is just as Tunisian. fastText labelled that one "other" and
#: "nhabet nbadel operateur" as English at 0.64 — it has no derja label, so a
#: confident verdict on this text is confidently wrong.
DERJA_MARKERS = {
    "el", "eli", "hedha", "hedhi", "hakka", "kifeh", "chnowa", "chneya", "chkoun",
    "wa9tech", "9adech", "barcha", "barsha", "yezzi", "walou", "chwaya", "tawa",
    "ghodwa", "lyoum", "lbera7", "bech", "nhab", "nhabet", "nheb", "nejjem",
    "najem", "mte3i", "mte3", "mta3", "mte3ha", "flous", "floussi", "fatoura",
    "khedma", "labes", "brabi", "sahbi", "chhar", "jom3a", "jomaa", "sbe7",
    "fel", "fil", "men", "m3a", "3la", "ala", "ken", "kif", "ama", "ama7",
    "mouch", "mech", "mesh", "manich", "mahouch", "ma", "makch", "famech",
    "fama", "thama", "andi", "3andi", "3andek", "3andhom", "nemchi", "temchi",
    "nbadel", "badel", "fasakh", "nsakker", "sakker", "talab", "chariti",
    "khalast", "khalas", "nkhalas", "3malt", "3mel", "jebt", "jeb", "wsal",
    "wsalni", "tsakker", "tetsakker", "ye5dem", "yekhdem", "khedem", "mochkla",
    "mochkel", "moshkel", "3otob", "khayeb", "batee", "sob", "aslema", "slem",
}

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
    except Exception as exc:  # noqa: BLE001 — LID must never break triage
        log.error("lid.load_failed", path=path, error=str(exc))
        return None


def model_available() -> bool:
    return _load_model() is not None


def detect(normalized: NormalizedText) -> LanguageResult:
    features = normalized.features

    # Arabic script is unambiguous — no model needed.
    if features.arabic_ratio >= ARABIC_SCRIPT_THRESHOLD:
        return LanguageResult("ar", min(1.0, features.arabic_ratio), "script")

    # Latin-script derja is decided here, BEFORE fastText, and without regard to
    # its confidence: there is no derja label to be confident about.
    derja = derja_share(normalized.text)
    if derja >= DERJA_THRESHOLD:
        return LanguageResult("ar-tn", round(derja, 3), "derja")

    return _fasttext_verdict(normalized.text) or _heuristic_verdict(normalized.text)


def derja_share(text: str) -> float:
    """Fraction of word-like tokens that are arabizi or known derja markers."""
    from app.intelligence.text.normalize import is_arabizi_token

    tokens = [
        token.strip(".,;:!?()[]\"'")
        for token in text.split()
        if any(character.isalpha() for character in token)
    ]
    if not tokens:
        return 0.0
    hits = sum(
        1 for token in tokens if is_arabizi_token(token) or token in DERJA_MARKERS
    )
    return hits / len(tokens)


def _fasttext_verdict(text: str) -> LanguageResult | None:
    model = _load_model()
    if model is None or not text.strip():
        return None

    # Call the underlying binding rather than model.predict(): the Python
    # wrapper in fasttext 0.9.2 finishes with `np.array(probs, copy=False)`,
    # which NumPy 2 refuses outright. Every prediction was raising and silently
    # dropping the system onto the stopword heuristic. `f.predict` returns plain
    # (probability, label) tuples and never touches NumPy.
    cleaned = text.replace("\n", " ")
    try:
        predictions = model.f.predict(cleaned, 1, 0.0, "strict")
        if not predictions:
            return None
        confidence, label = predictions[0]
    except Exception:  # noqa: BLE001 — last resort, try the wrapper
        try:
            labels, scores = model.predict(cleaned, k=1)
            label, confidence = labels[0], float(scores[0])
        except Exception as exc:  # noqa: BLE001 — heuristic takes over
            log.warning("lid.predict_failed", error=str(exc))
            return None

    code = str(label).replace("__label__", "")
    return LanguageResult(
        code if code in SUPPORTED else "other", float(confidence), "fasttext"
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

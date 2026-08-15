"""Language identification: fr | ar | ar-tn | en | other. Rule-based, no model.

This module used to lean on fastText's `lid.176.ftz`. That artifact was dropped
with the rest of the trained components: a 917 KB model file *is* a trained
model, and shipping one while claiming the system trains nothing is a
contradiction an examiner finds in thirty seconds.

Losing it costs less than it appears, because three of the four decisions never
used it:

*   **Arabic** is decided by script ratio. Unambiguous, no model needed.
*   **Derja** was never a fastText label at all. It has always been decided here,
    by arabizi patterns and a marker set — precisely because fastText called
    "3andi mochkla fel internet" Romanian and "nhabet nbadel operateur" English
    at 0.64 confidence. A confident verdict from a model with no label for the
    language is confidently wrong.
*   **French vs English** is the only decision that used it, and stopword
    overlap settles it: the two share almost no function words.

`ar-tn` remains our own call, taken before anything else looks at the text.
"""

from dataclasses import dataclass

from app.core.logging import get_logger
from app.intelligence.text.normalize import NormalizedText

log = get_logger(__name__)

SUPPORTED = {"fr", "ar", "en"}

#: Above this share of derja markers the text is Tunisian.
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


def model_available() -> bool:
    """Always False: there is no model. Kept so /health/ready keeps its shape."""
    return False


def detect(normalized: NormalizedText) -> LanguageResult:
    features = normalized.features

    # Arabic script is unambiguous.
    if features.arabic_ratio >= ARABIC_SCRIPT_THRESHOLD:
        return LanguageResult("ar", min(1.0, features.arabic_ratio), "script")

    # Latin-script derja, decided before anything else looks at the text.
    derja = derja_share(normalized.text)
    if derja >= DERJA_THRESHOLD:
        return LanguageResult("ar-tn", round(derja, 3), "derja")

    return _heuristic_verdict(normalized.text)


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


def _heuristic_verdict(text: str) -> LanguageResult:
    """French vs English by stopword overlap — they share almost no function words."""
    tokens = set(text.split())
    french = len(tokens & FRENCH_MARKERS)
    english = len(tokens & ENGLISH_MARKERS)

    if french == 0 and english == 0:
        return LanguageResult("other", 0.0, "heuristic")
    if french >= english:
        return LanguageResult("fr", french / (french + english), "heuristic")
    return LanguageResult("en", english / (french + english), "heuristic")

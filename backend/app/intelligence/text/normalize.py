"""Text normalisation for French, Arabic and Tunisian arabizi.

Pure functions, no I/O, no framework imports — unit-testable on their own.

The arabizi handling is the part that matters for Tunisia: people write derja in
Latin script with digits standing in for Arabic letters that have no Latin
equivalent ("3andi mochkla", "7aja", "9olt"). We keep BOTH forms — the Latin
original and an Arabic-script transliteration — so a complaint written as
"ma3andich reseau" and one written as "ما عنديش رزو" land near each other in
the same feature space.
"""

import re
import unicodedata
from dataclasses import dataclass

# --------------------------------------------------------------------------- regexes
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Tunisian mobile/fixed (+216 xx xxx xxx) and generic long digit runs.
PHONE_RE = re.compile(r"(?:\+?216[\s.-]?)?\b\d{2}[\s.-]?\d{3}[\s.-]?\d{3}\b")
QUOTED_LINE_RE = re.compile(r"^\s*>.*$", re.MULTILINE)
WHITESPACE_RE = re.compile(r"\s+")
REPEAT_RE = re.compile(r"(.)\1{2,}")
ARABIC_DIACRITICS_RE = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
TATWEEL_RE = re.compile(r"ـ")
ARABIC_CHAR_RE = re.compile(r"[؀-ۿ]")
LATIN_CHAR_RE = re.compile(r"[A-Za-z]")

#: Signature and forwarded-mail boilerplate, French and English.
SIGNATURE_PATTERNS = [
    re.compile(r"^--\s*$", re.MULTILINE),
    re.compile(r"^_{3,}\s*$", re.MULTILINE),
    re.compile(r"envoy[ée]\s+de\s+mon\s+(iphone|ipad|android|mobile|samsung)",
               re.IGNORECASE),
    re.compile(r"sent\s+from\s+my\s+\w+", re.IGNORECASE),
    re.compile(r"^\s*(cordialement|bien\s+cordialement|salutations\s+distingu[ée]es|"
               r"best\s+regards|regards)\s*[,.]?\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*le\s+\d{1,2}[/.]\d{1,2}[/.]\d{2,4}.*a\s+[ée]crit\s*:\s*$",
               re.IGNORECASE | re.MULTILINE),
]

# ------------------------------------------------------------------ arabizi mapping
#: Digit substitutions used across the Maghreb. Order matters: two-character
#: sequences are replaced before single characters.
ARABIZI_DIGRAPHS = {
    "'3": "غ", "'7": "خ", "'9": "ظ", "5'": "خ",
    "ch": "ش", "sh": "ش", "th": "ث", "kh": "خ", "gh": "غ", "ou": "و",
}
ARABIZI_DIGITS = {
    "2": "ء", "3": "ع", "4": "ذ", "5": "خ", "6": "ط", "7": "ح", "8": "غ", "9": "ق",
}
ARABIZI_LETTERS = {
    "a": "ا", "b": "ب", "c": "ك", "d": "د", "e": "ي", "f": "ف", "g": "ق",
    "h": "ه", "i": "ي", "j": "ج", "k": "ك", "l": "ل", "m": "م", "n": "ن",
    "o": "و", "p": "ب", "q": "ق", "r": "ر", "s": "س", "t": "ت", "u": "و",
    "v": "ف", "w": "و", "x": "كس", "y": "ي", "z": "ز",
}

#: A Latin token carrying one of these digits mid-word is almost certainly
#: arabizi rather than a reference number ("3andi" yes, "REC-2026" no).
ARABIZI_TOKEN_RE = re.compile(r"^[a-z]*[23579][a-z]+[a-z0-9]*$")


@dataclass(frozen=True)
class TextFeatures:
    char_count: int
    word_count: int
    exclamation_count: int
    question_count: int
    uppercase_ratio: float
    digit_ratio: float
    repeated_char_runs: int
    arabic_ratio: float
    latin_ratio: float
    arabizi_token_ratio: float
    has_attachment: bool = False


@dataclass(frozen=True)
class NormalizedText:
    #: Canonical form fed to the classifier and to dedup.
    text: str
    #: Arabic-script transliteration of arabizi tokens; empty when there are none.
    transliterated: str
    features: TextFeatures

    @property
    def indexable(self) -> str:
        """Both scripts concatenated — what we store and search over."""
        return f"{self.text} {self.transliterated}".strip() if self.transliterated else self.text


# ------------------------------------------------------------------------ pipeline
def strip_signatures(text: str) -> str:
    """Drop quoted history and signature blocks.

    Everything from the first signature marker onwards is removed: in practice
    that boundary is where the claimant's own words stop.
    """
    cleaned = QUOTED_LINE_RE.sub(" ", text)
    earliest = len(cleaned)
    for pattern in SIGNATURE_PATTERNS:
        match = pattern.search(cleaned)
        if match and match.start() < earliest:
            earliest = match.start()
    return cleaned[:earliest].strip() if earliest < len(cleaned) else cleaned.strip()


def mask_entities(text: str) -> str:
    """Replace URLs, emails and phone numbers with stable placeholders.

    They carry no category signal but would otherwise blow up the vocabulary and
    let a model memorise individual claimants.
    """
    text = URL_RE.sub(" <URL> ", text)
    text = EMAIL_RE.sub(" <EMAIL> ", text)
    return PHONE_RE.sub(" <PHONE> ", text)


def normalize_arabic(text: str) -> str:
    """Orthographic normalisation so spelling variants collapse to one form."""
    text = ARABIC_DIACRITICS_RE.sub("", text)
    text = TATWEEL_RE.sub("", text)
    for source, target in (
        ("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"),
        ("ة", "ه"), ("ى", "ي"), ("ؤ", "و"), ("ئ", "ي"),
    ):
        text = text.replace(source, target)
    return text


def collapse_repeats(text: str) -> tuple[str, int]:
    """`inacceptable!!!!!` -> `inacceptable!!`, and count how often it happened.

    The repetition is a genuine anger signal, so it is kept as a feature even
    though it is removed from the text.
    """
    runs = len(REPEAT_RE.findall(text))
    return REPEAT_RE.sub(r"\1\1", text), runs


def is_arabizi_token(token: str) -> bool:
    return bool(ARABIZI_TOKEN_RE.match(token))


def transliterate_arabizi(text: str) -> str:
    """Map arabizi tokens to Arabic script; leave everything else alone."""
    output: list[str] = []
    for token in text.split():
        if not is_arabizi_token(token):
            continue
        converted = token
        for source, target in ARABIZI_DIGRAPHS.items():
            converted = converted.replace(source, target)
        for source, target in ARABIZI_DIGITS.items():
            converted = converted.replace(source, target)
        converted = "".join(ARABIZI_LETTERS.get(ch, ch) for ch in converted)
        output.append(converted)
    return " ".join(output)


def extract_features(raw: str, has_attachment: bool = False) -> TextFeatures:
    """Measured on the RAW text — uppercase ratio is meaningless after lowercasing."""
    letters = [ch for ch in raw if ch.isalpha()]
    arabic = len(ARABIC_CHAR_RE.findall(raw))
    latin = len(LATIN_CHAR_RE.findall(raw))
    tokens = raw.lower().split()
    # Only word-like tokens count toward the arabizi share: phone numbers and
    # invoice references would otherwise dilute it and hide genuine derja.
    word_tokens = [token for token in tokens if any(ch.isalpha() for ch in token)]
    arabizi_tokens = sum(1 for token in word_tokens if is_arabizi_token(token))

    return TextFeatures(
        char_count=len(raw),
        word_count=len(tokens),
        exclamation_count=raw.count("!"),
        question_count=raw.count("?"),
        uppercase_ratio=(
            sum(1 for ch in letters if ch.isupper()) / len(letters) if letters else 0.0
        ),
        digit_ratio=(
            sum(1 for ch in raw if ch.isdigit()) / len(raw) if raw else 0.0
        ),
        repeated_char_runs=len(REPEAT_RE.findall(raw)),
        arabic_ratio=arabic / len(letters) if letters else 0.0,
        latin_ratio=latin / len(letters) if letters else 0.0,
        arabizi_token_ratio=arabizi_tokens / len(word_tokens) if word_tokens else 0.0,
        has_attachment=has_attachment,
    )


def normalize(
    subject: str = "", body: str = "", *, has_attachment: bool = False
) -> NormalizedText:
    """Full pipeline: subject + body in, canonical text and features out.

    The subject is repeated once. That doubles its weight in the TF-IDF space
    for free, without a custom feature (spec 5.3).
    """
    raw = f"{subject} {subject} {body}".strip() if subject else body.strip()
    features = extract_features(raw, has_attachment=has_attachment)

    text = strip_signatures(raw)
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = mask_entities(text)
    text = normalize_arabic(text)
    text, _ = collapse_repeats(text)
    text = WHITESPACE_RE.sub(" ", text).strip()

    return NormalizedText(
        text=text, transliterated=transliterate_arabizi(text), features=features
    )

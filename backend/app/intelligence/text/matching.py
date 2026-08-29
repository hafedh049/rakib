"""Term matching over normalised text.

Lives here rather than beside the categoriser because both the lexicon and the
department router need it, and neither should have to import the other.

Terms are written unaccented and lower case, and are matched against
accent-folded text — see NormalizedText.indexable.
"""

import re

TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)


def find_terms(text: str, terms: list[str]) -> list[str]:
    """Return the terms present in `text`.

    Multi-word terms match as substrings; single words match against the token
    set, so "pas" does not fire inside "passer". That asymmetry is deliberate:
    a phrase is unambiguous, a short word is not.
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

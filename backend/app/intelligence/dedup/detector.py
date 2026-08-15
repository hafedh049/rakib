"""Duplicate and related-complaint detection.

Two stages, cheap then precise (spec 5.5). Candidate generation is a Mongo query
owned by the caller; this module only scores.

The asymmetry between same-claimant and cross-claimant matches is the important
part: one person filing the same complaint twice is a duplicate, but forty
people describing the same outage is an incident cluster. Treating the second
case as duplication would silently hide a mass failure, so cross-claimant
matches need a much higher score and are tagged `related`, never `duplicate`.
"""

from dataclasses import dataclass

from rapidfuzz import fuzz

from app.intelligence.ports import DedupCandidate

SHINGLE_SIZE = 5

#: Two complementary views of "the same complaint, said twice". The token-set
#: ratio forgives reordering and small edits; shingle overlap catches copied
#: passages. Neither is fooled by the same things, which is the point of using
#: both — and both are exact, so a duplicate flag can be explained to a client.
WEIGHT_FUZZ = 0.6
WEIGHT_JACCARD = 0.4

#: Same claimant is weak evidence on its own, so it nudges rather than decides.
SAME_CLAIMANT_BONUS = 0.05


@dataclass(frozen=True)
class DedupMatch:
    candidate_id: str
    score: float
    same_claimant: bool
    fuzz_ratio: float
    jaccard: float

    @property
    def relation(self) -> str:
        return "duplicate" if self.same_claimant else "related"


def shingles(text: str, size: int = SHINGLE_SIZE) -> set[str]:
    words = text.split()
    if len(words) < size:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + size]) for i in range(len(words) - size + 1)}


def jaccard(left: str, right: str) -> float:
    first, second = shingles(left), shingles(right)
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def score_candidate(
    text: str,
    subject: str,
    candidate: DedupCandidate,
    claimant_email: str | None,
) -> DedupMatch:
    ratio = fuzz.token_set_ratio(subject, candidate.subject) / 100.0
    overlap = jaccard(text, candidate.normalized_text)
    score = WEIGHT_FUZZ * ratio + WEIGHT_JACCARD * overlap

    same_claimant = bool(
        claimant_email
        and candidate.claimant_email
        and claimant_email.lower() == candidate.claimant_email.lower()
    )
    if same_claimant:
        score = min(1.0, score + SAME_CLAIMANT_BONUS)

    return DedupMatch(
        candidate_id=candidate.id,
        score=round(score, 4),
        same_claimant=same_claimant,
        fuzz_ratio=round(ratio, 4),
        jaccard=round(overlap, 4),
    )


def detect(
    text: str,
    subject: str,
    candidates: list[DedupCandidate],
    claimant_email: str | None = None,
    *,
    auto_threshold: float = 0.82,
    suggest_threshold: float = 0.65,
    cross_claimant_threshold: float = 0.90,
) -> tuple[DedupMatch | None, list[DedupMatch]]:
    """Return (auto_linked_duplicate, other_matches_worth_showing).

    Never auto-closes anything: the duplicate is flagged and the complaint is
    still routed normally. Closing is always a human decision (spec 5.5).
    """
    if not candidates or not text.strip():
        return None, []

    matches = sorted(
        (
            score_candidate(text, subject, candidate, claimant_email)
            for candidate in candidates
        ),
        key=lambda match: match.score,
        reverse=True,
    )

    duplicate: DedupMatch | None = None
    best = matches[0]
    threshold = auto_threshold if best.same_claimant else cross_claimant_threshold
    if best.score >= threshold:
        duplicate = best

    suggestions = [
        match
        for match in matches
        if match.score >= suggest_threshold and match is not duplicate
    ][:5]
    return duplicate, suggestions

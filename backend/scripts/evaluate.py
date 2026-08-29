"""Evaluate the category lexicon.

    python -m scripts.evaluate

Measures the classifier against the hand-written gold set in scripts/gold.py —
independent of the lexicon, and deliberately including cases that have no single
correct answer, where abstaining is the right behaviour.

Reported: macro-F1, accuracy, the abstention rate, and precision on the subset
where the classifier actually committed to a category.

That last number is the one that matters operationally. Abstention is not
failure — an uncategorised complaint is still routed by keyword and still
reaches an agent — but a wrong category shown confidently costs an agent more
time than no category at all. A rising abstention rate means the vocabulary is
drifting away from how people write; a falling precision means it is guessing.
"""

from app.intelligence.lexicon.classifier import classify
from app.intelligence.lexicon.terms import CATEGORY_LEXICON
from app.intelligence.text.normalize import normalize
from scripts.gold import GOLD


def macro_f1(pairs: list[tuple[str, str | None]]) -> tuple[float, float]:
    """(macro-F1, accuracy) over (expected, predicted)."""
    labels = {expected for expected, _ in pairs}
    f1s = []
    for label in labels:
        tp = sum(1 for e, p in pairs if e == label and p == label)
        fp = sum(1 for e, p in pairs if e != label and p == label)
        fn = sum(1 for e, p in pairs if e == label and p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )
    accuracy = sum(1 for e, p in pairs if e == p) / len(pairs) if pairs else 0.0
    return (sum(f1s) / len(f1s) if f1s else 0.0), accuracy


def predict(subject: str, body: str) -> str | None:
    return classify(normalize(subject, body).indexable).category


def evaluate_gold() -> None:
    labelled = [(s, b, c) for s, b, c in GOLD if c is not None]
    unlabelled = [(s, b) for s, b, c in GOLD if c is None]

    pairs = [(c, predict(s, b)) for s, b, c in labelled]
    f1, accuracy = macro_f1(pairs)
    abstained = sum(1 for _, p in pairs if p is None)

    committed = [(e, p) for e, p in pairs if p is not None]
    correct = sum(1 for e, p in committed if e == p)

    print(f"\n=== GOLD (authored, independent)  (n={len(pairs)}) ===")
    print(f"macro-F1 {f1:.3f}   accuracy {accuracy:.3f}")
    print(f"abstained on {abstained}/{len(pairs)} ({abstained / len(pairs):.0%})")
    if committed:
        print(
            f"when it committed: {correct}/{len(committed)} correct "
            f"({correct / len(committed):.0%})"
        )

    if unlabelled:
        routed = sum(1 for s, b in unlabelled if predict(s, b) is None)
        print(f"\n=== unclassifiable  (n={len(unlabelled)}) ===")
        print(f"correctly routed to human triage: {routed / len(unlabelled):.0%}")


def main() -> None:
    terms = sum(len(t) for t in CATEGORY_LEXICON.values())
    print(f"lexicon: {terms} terms across {len(CATEGORY_LEXICON)} categories")
    evaluate_gold()
    print(
        "\n"
        "==============================================================\n"
        "The gold set is written by hand, independently of the lexicon,\n"
        "and includes cases meant to have no single correct answer.\n"
        "\n"
        "Abstention is where the vocabulary shows its edges: text phrased\n"
        "outside the lexicon scores zero and goes to an agent. That is the\n"
        "designed behaviour — the suggestion exists to save an agent time,\n"
        "never to decide in their place.\n"
        "=============================================================="
    )


if __name__ == "__main__":
    main()

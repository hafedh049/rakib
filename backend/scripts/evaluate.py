"""Evaluate the deterministic lexicon classifier.

    python -m scripts.evaluate

The trained model is gone, but the evaluation discipline is not. This measures
the lexicon against exactly the sets the model was held to — the hand-authored
gold set and the wild set of real reviews it never saw — so the two are
comparable and the cost of dropping the model is a number rather than a claim.

There is no holdout here, and that absence is the point: a lexicon cannot
memorise a training corpus, so the holdout/gold gap that dominated the previous
evaluation simply does not exist. What remains is the harder question — how much
real complaint text falls outside the vocabulary.
"""

import json
from collections import Counter
from pathlib import Path

from app.intelligence.lexicon.classifier import classify
from app.intelligence.lexicon.terms import CATEGORY_LEXICON
from app.intelligence.text.normalize import normalize
from scripts.gold import GOLD

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


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

    print(f"\n=== GOLD (authored, independent)  (n={len(pairs)}) ===")
    print(f"macro-F1 {f1:.3f}   accuracy {accuracy:.3f}")
    print(f"abstained on {abstained}/{len(pairs)} ({abstained / len(pairs):.0%})")

    if unlabelled:
        routed = sum(1 for s, b in unlabelled if predict(s, b) is None)
        print(f"\n=== unclassifiable  (n={len(unlabelled)}) ===")
        print(f"correctly routed to human triage: {routed / len(unlabelled):.0%}")


def evaluate_wild() -> None:
    """Reported, but NOT a valid score for this classifier. See the warning.

    The wild set's labels were produced by scripts/labeling.py, whose vocabulary
    is built from SUBCATEGORY_TERMS — the same terms the lexicon is built from.
    Scoring the lexicon against them measures the lexicon against itself, and it
    duly returns ~0.99.

    The number was meaningful for the trained model, which learned a different
    signal (TF-IDF over authored text) and was genuinely tested by weak labels.
    It became circular the moment the classifier and the labeller shared a
    vocabulary. It is printed only so the circularity is visible rather than
    quietly dropped, and so nobody quotes it as a result.
    """
    path = DATA_DIR / "wild.jsonl"
    if not path.exists():
        print("\n(no wild set)")
        return

    rows = [json.loads(line) for line in path.open(encoding="utf-8")]
    pairs = [
        (row["category"], predict(row.get("subject", ""), row["text"]))
        for row in rows
        if row.get("category")
    ]
    f1, accuracy = macro_f1(pairs)
    abstained = sum(1 for _, p in pairs if p is None)

    print(f"\n=== WILD (real reviews)  (n={len(pairs)}) ===")
    print("!! CIRCULAR — NOT A RESULT !!")
    print("   These labels came from the weak labeller, which shares its")
    print("   vocabulary with this lexicon. This measures the lexicon against")
    print("   itself. Valid for the trained model; meaningless here.")
    print(f"macro-F1 {f1:.3f}   accuracy {accuracy:.3f}   <- ignore both")
    print(f"abstained on {abstained}/{len(pairs)} ({abstained / len(pairs):.0%})")

    misses = Counter(
        expected for expected, predicted in pairs if predicted != expected
    )
    if misses:
        print("worst classes:")
        for label, count in misses.most_common(5):
            print(f"  {count:4d}  {label}")


def main() -> None:
    terms = sum(len(t) for t in CATEGORY_LEXICON.values())
    print(f"lexicon: {terms} terms across {len(CATEGORY_LEXICON)} categories")
    print("no trained model, no artifacts, no holdout")
    evaluate_gold()
    evaluate_wild()
    print(
        "\n"
        "==============================================================\n"
        "The gold set is the only valid number here: it was written by\n"
        "hand, independently of the lexicon, and includes cases meant to\n"
        "be unclassifiable.\n"
        "\n"
        "For the record, the trained model this replaced scored gold 0.851.\n"
        "Dropping it is a real loss of generalisation, and abstention is\n"
        "where it shows: text phrased outside the vocabulary scores zero.\n"
        "Those complaints are routed to a human, which is the designed\n"
        "behaviour and what the circulaire assumes anyway — Article 9 asks\n"
        "for routing, alerting and KPIs, never for automatic classification.\n"
        "=============================================================="
    )


if __name__ == "__main__":
    main()

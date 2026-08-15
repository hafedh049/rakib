"""Rules engine: scoring, explainability, sentiment, and the priority buckets."""

import pytest

from app.domain.taxonomy import Category
from app.intelligence.rules.defaults import DEFAULT_RULES
from app.intelligence.rules.engine import (
    RuleContext,
    RuleSpec,
    analyse_sentiment,
    bucket_priority,
    bucket_sentiment,
    evaluate,
    evaluate_rule,
    find_terms,
)
from app.intelligence.rules.subcategory import detect_subcategory
from app.intelligence.text.normalize import normalize

ALL_SPECS = [
    RuleSpec(
        code=r["code"], label=r["label"], kind=r["kind"],
        weight=r["weight"], config=r["config"], order=r["order"],
    )
    for r in DEFAULT_RULES
]


def context_for(subject: str = "", body: str = "", **kwargs) -> RuleContext:
    normalized = normalize(subject, body, has_attachment=kwargs.get("attachment_count", 0) > 0)
    return RuleContext(
        text=normalized.text,
        transliterated=normalized.transliterated,
        features=normalized.features,
        **kwargs,
    )


# ------------------------------------------------------------------------ matching
def test_single_words_match_on_token_boundaries():
    """`pas` must not fire inside `passer` — the classic lexicon false positive."""
    assert find_terms("je vais passer demain", ["pas"]) == []
    assert find_terms("je ne suis pas satisfait", ["pas"]) == ["pas"]


def test_multiword_terms_match_as_substrings():
    assert find_terms("cela dure depuis des semaines", ["depuis des semaines"])


def test_matching_is_case_insensitive_via_normalisation():
    context = context_for(body="C'EST INACCEPTABLE")
    assert find_terms(context.searchable, ["inacceptable"])


# ------------------------------------------------------------------- rule kinds
def test_lexicon_rule_reports_the_tokens_that_fired():
    rule = RuleSpec(
        code="X", label="Urgence", kind="lexicon", weight=10,
        config={"terms": ["urgent", "inacceptable"], "cap": 2},
    )
    hit = evaluate_rule(rule, context_for(body="c'est urgent et inacceptable"))
    assert hit is not None
    assert set(hit.matched) == {"urgent", "inacceptable"}
    assert hit.weight == 20  # two matches, cap 2


def test_lexicon_cap_limits_the_multiplier():
    rule = RuleSpec(
        code="X", label="Urgence", kind="lexicon", weight=10,
        config={"terms": ["urgent", "inacceptable", "scandaleux"], "cap": 1},
    )
    hit = evaluate_rule(rule, context_for(body="urgent inacceptable scandaleux"))
    assert hit.weight == 10


def test_inactive_rules_never_fire():
    rule = RuleSpec(
        code="X", label="X", kind="lexicon", weight=99,
        config={"terms": ["urgent"]}, active=False,
    )
    assert evaluate_rule(rule, context_for(body="urgent")) is None


def test_regex_rule_reports_its_matches():
    rule = RuleSpec(
        code="AMOUNT", label="Montant", kind="regex", weight=8,
        config={"pattern": r"\b\d{2,5}\s*(?:dinars?|dt)\b", "flags": "i"},
    )
    hit = evaluate_rule(rule, context_for(body="on m'a preleve 187 dinars ce mois"))
    assert hit is not None
    assert "187 dinars" in hit.matched


def test_invalid_regex_is_ignored_rather_than_raising():
    rule = RuleSpec(
        code="BAD", label="Bad", kind="regex", weight=5, config={"pattern": "([unclosed"}
    )
    assert evaluate_rule(rule, context_for(body="anything")) is None


def test_field_rule_on_vip():
    rule = RuleSpec(
        code="VIP", label="VIP", kind="field", weight=25,
        config={"path": "claimant_is_vip", "op": "eq", "value": True},
    )
    assert evaluate_rule(rule, context_for(body="x", claimant_is_vip=True)) is not None
    assert evaluate_rule(rule, context_for(body="x", claimant_is_vip=False)) is None


def test_history_rule_needs_the_minimum_count():
    rule = RuleSpec(
        code="REPEAT", label="Repeat", kind="history", weight=20,
        config={"source": "prior_count_30d", "min_count": 3},
    )
    assert evaluate_rule(rule, context_for(body="x", prior_count_30d=2)) is None
    hit = evaluate_rule(rule, context_for(body="x", prior_count_30d=4))
    assert hit.matched == ["prior_count_30d=4"]


def test_length_rule_penalises_very_short_messages():
    rule = RuleSpec(
        code="SHORT", label="Court", kind="length", weight=-8, config={"max": 60}
    )
    assert evaluate_rule(rule, context_for(body="panne")) is not None
    long_body = "mon virement de salaire n est toujours pas arrive depuis mardi " * 4
    assert evaluate_rule(rule, context_for(body=long_body)) is None


def test_category_weight_rule():
    rule = RuleSpec(
        code="CAT", label="Categorie", kind="category_weight", weight=1,
        config={"map": {Category.FRAIS_COMMISSIONS: 10}},
    )
    hit = evaluate_rule(rule, context_for(body="x", category=Category.FRAIS_COMMISSIONS))
    assert hit.weight == 10
    assert evaluate_rule(rule, context_for(body="x", category=Category.CHEQUE_EFFET)) is None


# ------------------------------------------------------------------------ buckets
@pytest.mark.parametrize(
    "score,priority", [(0, 4), (19, 4), (20, 3), (44, 3), (45, 2), (69, 2), (70, 1), (200, 1)]
)
def test_priority_buckets(score, priority):
    assert bucket_priority(score) == priority


def test_score_never_goes_negative():
    """A very short message alone must not produce a negative score."""
    result = evaluate(ALL_SPECS, context_for(body="panne"))
    assert result.priority_score >= 0


# ------------------------------------------------------- end-to-end scoring shape
def test_routine_complaint_is_normal_priority():
    result = evaluate(
        ALL_SPECS,
        context_for(
            "Question sur mes frais",
            "Bonjour, je souhaite comprendre le detail des frais du mois. Merci.",
            category=Category.FRAIS_COMMISSIONS,
        ),
    )
    assert result.priority == 3


def test_legal_threat_escalates():
    result = evaluate(
        ALL_SPECS,
        context_for(
            "Mise en demeure",
            "Sans reponse sous 8 jours je saisis mon avocat et je depose plainte "
            "au tribunal. Cela dure depuis des semaines.",
            category=Category.FRAIS_COMMISSIONS,
        ),
    )
    assert result.priority <= 2
    assert any(hit.code == "LEGAL_LEXICON_FR" for hit in result.hits)


def test_vip_with_legal_threat_and_history_is_critical():
    result = evaluate(
        ALL_SPECS,
        context_for(
            "URGENT - mise en demeure",
            "C'est inacceptable, aucune reponse depuis des semaines. Mon avocat "
            "va deposer plainte. Je vais cloturer mon compte et changer de banque. "
            "Toute la zone est touchee.",
            category=Category.FRAIS_COMMISSIONS,
            claimant_is_vip=True,
            prior_count_30d=4,
            prior_open=3,
        ),
    )
    assert result.priority == 1
    assert result.urgency_score > 0.6


def test_every_hit_carries_matched_tokens():
    """No explainability, no feature — this is the spec's explicit requirement."""
    result = evaluate(
        ALL_SPECS,
        context_for(
            "Urgent", "Inacceptable, mon avocat va porter plainte, 187 dinars preleves",
            claimant_is_vip=True,
        ),
    )
    assert result.hits
    assert all(hit.matched for hit in result.hits)


def test_arabic_complaint_fires_arabic_lexicons():
    result = evaluate(
        ALL_SPECS,
        context_for("مشكل عاجل", "عاجل، من اسابيع ما فماش شبكة و غير مقبول"),
    )
    assert any(hit.code == "URGENCY_LEXICON_AR" for hit in result.hits)


def test_arabizi_complaint_fires_derja_lexicon():
    result = evaluate(
        ALL_SPECS,
        context_for("mochkel", "3andi mochkla kbira, yezzi barcha, ma yenjemch"),
    )
    assert any(hit.code == "URGENCY_LEXICON_TN" for hit in result.hits)


# ---------------------------------------------------------------------- sentiment
@pytest.mark.parametrize(
    "score,label",
    [(-0.9, "angry"), (-0.3, "frustrated"), (0.0, "neutral"), (0.8, "positive")],
)
def test_sentiment_buckets(score, label):
    assert bucket_sentiment(score) == label


def test_negation_flips_polarity():
    """`pas satisfait` must not read as positive."""
    positive, _ = analyse_sentiment(context_for(body="je suis satisfait du service"))
    negated, _ = analyse_sentiment(context_for(body="je ne suis pas satisfait du service"))
    assert positive == "positive"
    assert negated in {"angry", "frustrated"}


def test_shouting_pushes_sentiment_down():
    calm, calm_score = analyse_sentiment(context_for(body="il y a un probleme sur mon compte"))
    shouted, shouted_score = analyse_sentiment(
        context_for(body="IL Y A UN PROBLEME SUR MON COMPTE !!!")
    )
    assert shouted_score < calm_score
    assert calm or shouted  # both produced a label


def test_thankful_message_is_positive():
    label, score = analyse_sentiment(
        context_for(body="merci beaucoup, probleme resolu, service excellent et rapide")
    )
    assert label == "positive"
    assert score > 0


def test_sentiment_score_stays_in_range():
    for body in ["merci " * 50, "inacceptable scandaleux honteux " * 20, ""]:
        _, score = analyse_sentiment(context_for(body=body or "x"))
        assert -1.0 <= score <= 1.0


# -------------------------------------------------------------------- subcategory
@pytest.mark.parametrize(
    "category,body,expected",
    [
        (Category.FRAIS_COMMISSIONS, "des agios sur mon decouvert", "agios"),
        (Category.CARTE_BANCAIRE, "ma carte a ete avalee par le distributeur", "carte_avalee"),
        (Category.BANQUE_DIGITALE, "impossible de faire le login", "connexion_impossible"),
    ],
)
def test_subcategory_detection(category, body, expected):
    assert detect_subcategory(category, normalize(body=body).indexable) == expected


def test_subcategory_is_none_without_a_category():
    assert detect_subcategory(None, "n'importe quel texte") is None


def test_subcategory_is_none_when_nothing_matches():
    assert detect_subcategory(Category.FRAIS_COMMISSIONS, "bonjour") is None

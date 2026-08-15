"""Language identification and the cold-start rules-only engine."""

import pytest

from app.intelligence.engines.rules_only import (
    RulesOnlyTriageEngine,
    route_by_keywords,
    top_keywords,
)
from app.intelligence.ports import DepartmentInfo, TriageInput
from app.intelligence.text import language as lid
from app.intelligence.text.normalize import normalize

DEPARTMENTS = [
    DepartmentInfo(
        code="FACTURATION", name="Facturation",
        keywords=["facture", "montant", "prelevement", "recharge", "solde", "ligne"],
        categories=["FACTURATION", "PAIEMENT_RECHARGE"],
    ),
    DepartmentInfo(
        code="RESEAU_MOBILE", name="Reseau Mobile",
        keywords=["reseau", "signal", "couverture", "4g", "appel", "ligne"],
        categories=["RESEAU_MOBILE", "ROAMING_INTERNATIONAL"],
    ),
    DepartmentInfo(
        code="FIXE_INTERVENTION", name="Fixe et Intervention",
        keywords=["fibre", "adsl", "technicien", "panne", "box", "ligne"],
        categories=["INTERNET_FIXE", "INTERVENTION_TECHNIQUE"],
    ),
]


# ------------------------------------------------------------------------ language
def test_arabic_script_is_detected_without_the_model():
    result = lid.detect(normalize(body="من ثلاثة أيام ما فماش شبكة في الحي"))
    assert result.code == "ar"
    assert result.source == "script"


def test_french_is_detected():
    result = lid.detect(
        normalize(body="Je vous ecris car ma facture est incorrecte depuis deux mois")
    )
    assert result.code == "fr"


def test_english_is_detected():
    result = lid.detect(
        normalize(body="The network has been down for three days and no one answers")
    )
    assert result.code in {"en", "other"}


def test_arabizi_is_labelled_ar_tn():
    """Latin-script Tunisian is our own decision layer."""
    result = lid.detect(
        normalize(body="3andi mochkla fel internet, 7atta lyoum ma7alouhech, yezzi")
    )
    assert result.code == "ar-tn"
    assert result.source == "derja"


@pytest.mark.parametrize(
    "text",
    [
        # No digit substitution at all — the arabizi pattern misses these, and
        # Pure lexical derja: no digit substitution to lean on.
        "el fatoura mte3i hedha chhar 210 dinar w ana ma badeltech fel offre",
        "nhabet nbadel operateur, 3malt talab fasakh men jomaa",
        "9adech hedha? barcha flous w el khedma khayba",
    ],
)
def test_plain_derja_is_not_mistaken_for_french_or_english(text):
    """Derja is decided first, before French or English are even considered."""
    assert lid.detect(normalize(body=text)).code == "ar-tn"


def test_french_is_not_swallowed_by_the_derja_rule():
    """The marker set must not be so greedy that ordinary French trips it."""
    for text in [
        "Bonjour, ma facture de janvier est incorrecte et personne ne repond",
        "Je souhaite resilier mon abonnement et transferer mon numero",
        "Le technicien n est jamais venu au rendez-vous de jeudi matin",
    ]:
        assert lid.detect(normalize(body=text)).code == "fr"


def test_language_detection_never_raises_on_empty_text():
    assert lid.detect(normalize(body="")).code in {"fr", "en", "ar", "ar-tn", "other"}


# ------------------------------------------------------------------------- routing
@pytest.mark.parametrize(
    "body,expected",
    [
        ("ma facture de janvier est trop elevee, montant anormal", "FACTURATION"),
        ("aucun signal, pas de couverture 4g dans ma zone", "RESEAU_MOBILE"),
        ("la fibre est en panne, envoyez un technicien", "FIXE_INTERVENTION"),
    ],
)
def test_keyword_routing_picks_the_right_department(body, expected):
    code, _ = route_by_keywords(normalize(body=body).indexable, DEPARTMENTS)
    assert code == expected


def test_shared_keywords_carry_less_weight_than_discriminating_ones():
    """`ligne` appears in every department, so it must not decide the routing."""
    code, _ = route_by_keywords(
        normalize(body="probleme sur ma ligne, la fibre est en panne").indexable,
        DEPARTMENTS,
    )
    assert code == "FIXE_INTERVENTION"


def test_unroutable_text_falls_back_to_general():
    code, alternatives = route_by_keywords(
        normalize(body="bonjour comment allez vous").indexable, DEPARTMENTS
    )
    assert code == "GENERAL"
    assert alternatives == []


def test_routing_offers_the_department_categories_as_alternatives():
    _, alternatives = route_by_keywords(
        normalize(body="ma facture est fausse").indexable, DEPARTMENTS
    )
    assert [category for category, _ in alternatives] == [
        "FACTURATION", "PAIEMENT_RECHARGE"
    ]


def test_top_keywords_skips_short_words_and_placeholders():
    keywords = top_keywords("la facture facture est <url> tres elevee elevee elevee")
    assert keywords[0] == "elevee"
    assert "<url>" not in keywords
    assert "la" not in keywords


# ------------------------------------------------------------- cold-start engine
@pytest.fixture
def engine():
    from app.intelligence.rules.defaults import DEFAULT_RULES
    from app.intelligence.rules.engine import RuleSpec

    return RulesOnlyTriageEngine([
        RuleSpec(
            code=r["code"], label=r["label"], kind=r["kind"],
            weight=r["weight"], config=r["config"], order=r["order"],
        )
        for r in DEFAULT_RULES
    ])


async def test_cold_start_engine_routes_without_any_model(engine):
    output = await engine.analyze(
        TriageInput(
            subject="Facture trop elevee",
            body="Ma facture de janvier s'eleve a 187 dinars, montant anormal.",
            departments=DEPARTMENTS,
        )
    )
    assert output.department_code == "FACTURATION"
    assert output.engine == "rules"


async def test_cold_start_admits_it_cannot_categorise(engine):
    """It routes honestly and asks for a human rather than inventing a label."""
    output = await engine.analyze(
        TriageInput(subject="Facture", body="montant anormal", departments=DEPARTMENTS)
    )
    assert output.category is None
    assert output.category_confidence == 0.0
    assert output.needs_human_triage is True
    assert output.triage_reason == "no_model"


async def test_cold_start_still_prioritises_and_explains(engine):
    output = await engine.analyze(
        TriageInput(
            subject="URGENT",
            body="Inacceptable ! Mon avocat va porter plainte, depuis des semaines "
                 "aucune reponse. Toute la rue est touchee.",
            claimant_is_vip=True,
            claimant_prior_count_30d=4,
            departments=DEPARTMENTS,
        )
    )
    assert output.priority == 1
    assert output.rule_hits
    assert all(hit.matched for hit in output.rule_hits)


async def test_engine_records_stage_latencies(engine):
    output = await engine.analyze(
        TriageInput(subject="x", body="ma facture est fausse", departments=DEPARTMENTS)
    )
    assert [stage["name"] for stage in output.stages] == [
        "normalize", "language", "route", "rules"
    ]
    assert all("latency_ms" in stage for stage in output.stages)


async def test_engine_is_fast(engine):
    """Target is under 50 ms end to end (spec 5)."""
    output = await engine.analyze(
        TriageInput(
            subject="Facture anormale",
            body="Ma facture de janvier s'eleve a 187 dinars " * 20,
            departments=DEPARTMENTS,
        )
    )
    assert output.latency_ms < 50


def test_engine_health_reports_degraded(engine):
    health = engine.health()
    assert health.ready is True
    assert health.degraded is True
    assert health.engine_ready is False

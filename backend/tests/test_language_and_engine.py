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
        code="FRAIS_COMMISSIONS", name="Facturation",
        keywords=["frais", "agios", "commission", "montant", "compte", "operation"],
        categories=["FRAIS_COMMISSIONS", "PAIEMENT_TPE_ECOMMERCE"],
    ),
    DepartmentInfo(
        code="MONETIQUE", name="Monetique et Cartes",
        keywords=["carte", "distributeur", "retrait", "plafond", "tpe", "operation"],
        categories=["CARTE_BANCAIRE", "OPERATIONS_INTERNATIONALES"],
    ),
    DepartmentInfo(
        code="OPERATIONS", name="Fixe et Intervention",
        keywords=["virement", "cheque", "rib", "prelevement", "chequier", "operation"],
        categories=["VIREMENT_PRELEVEMENT", "DAB_GAB"],
    ),
]


# ------------------------------------------------------------------------ language
def test_arabic_script_is_detected_without_the_model():
    result = lid.detect(normalize(body="من ثلاثة أيام ما فماش شبكة في الحي"))
    assert result.code == "ar"
    assert result.source == "script"


def test_french_is_detected():
    result = lid.detect(
        normalize(body="Je vous ecris car mon releve est incorrect depuis deux mois")
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
        "Bonjour, mon releve de janvier est incorrect et personne ne repond",
        "Je souhaite cloturer mon compte et transferer mes avoirs ailleurs",
        "Le conseiller n est jamais revenu vers moi apres notre rendez-vous",
    ]:
        assert lid.detect(normalize(body=text)).code == "fr"


def test_language_detection_never_raises_on_empty_text():
    assert lid.detect(normalize(body="")).code in {"fr", "en", "ar", "ar-tn", "other"}


# ------------------------------------------------------------------------- routing
@pytest.mark.parametrize(
    "body,expected",
    [
        ("des agios de 78 dinars, montant anormal sur mon compte", "FRAIS_COMMISSIONS"),
        ("le distributeur a garde ma carte, retrait impossible", "MONETIQUE"),
        ("mon virement n est pas arrive, le rib etait correct", "OPERATIONS"),
    ],
)
def test_keyword_routing_picks_the_right_department(body, expected):
    code, _ = route_by_keywords(normalize(body=body).indexable, DEPARTMENTS)
    assert code == expected


def test_shared_keywords_carry_less_weight_than_discriminating_ones():
    """`operation` appears in every department, so it must not decide routing."""
    code, _ = route_by_keywords(
        normalize(body="probleme sur une operation, mon cheque est rejete").indexable,
        DEPARTMENTS,
    )
    assert code == "OPERATIONS"


def test_unroutable_text_falls_back_to_general():
    code, alternatives = route_by_keywords(
        normalize(body="bonjour comment allez vous").indexable, DEPARTMENTS
    )
    assert code == "GENERAL"
    assert alternatives == []


def test_routing_offers_the_department_categories_as_alternatives():
    _, alternatives = route_by_keywords(
        normalize(body="des agios injustifies sur mon compte").indexable, DEPARTMENTS
    )
    assert [category for category, _ in alternatives] == [
        "FRAIS_COMMISSIONS", "PAIEMENT_TPE_ECOMMERCE"
    ]


def test_top_keywords_skips_short_words_and_placeholders():
    keywords = top_keywords("les agios agios sont <url> tres eleves eleves eleves")
    assert keywords[0] == "eleves"
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
            subject="Agios trop eleves",
            body="Des agios de 187 dinars ont ete preleves, montant anormal.",
            departments=DEPARTMENTS,
        )
    )
    assert output.department_code == "FRAIS_COMMISSIONS"
    assert output.engine == "rules"


async def test_cold_start_admits_it_cannot_categorise(engine):
    """It routes honestly and asks for a human rather than inventing a label."""
    output = await engine.analyze(
        TriageInput(subject="Frais", body="montant anormal", departments=DEPARTMENTS)
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
        TriageInput(subject="x", body="des agios injustifies", departments=DEPARTMENTS)
    )
    assert [stage["name"] for stage in output.stages] == [
        "normalize", "language", "route", "rules"
    ]
    assert all("latency_ms" in stage for stage in output.stages)


async def test_engine_is_fast(engine):
    """Target is under 50 ms end to end (spec 5)."""
    output = await engine.analyze(
        TriageInput(
            subject="Agios anormaux",
            body="Des agios de 187 dinars ont ete preleves a tort " * 20,
            departments=DEPARTMENTS,
        )
    )
    assert output.latency_ms < 50


def test_engine_health_reports_degraded(engine):
    health = engine.health()
    assert health.ready is True
    assert health.degraded is True

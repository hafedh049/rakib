"""Language identification, the lexicon, and department routing."""

import pytest

from app.intelligence.engines.lexicon import (
    LexiconTriageEngine,
    route_by_keywords,
    top_keywords,
)
from app.intelligence.lexicon.classifier import classify
from app.intelligence.ports import DepartmentInfo, TriageInput
from app.intelligence.text import language as lid
from app.intelligence.text.normalize import normalize

DEPARTMENTS = [
    DepartmentInfo(
        code="MONETIQUE", name="Monetique et Cartes",
        keywords=["carte", "distributeur", "retrait", "tpe", "operation"],
        categories=["CARTE_BANCAIRE", "DAB_GAB", "PAIEMENT_TPE_ECOMMERCE"],
    ),
    DepartmentInfo(
        code="OPERATIONS", name="Operations Bancaires",
        keywords=["virement", "cheque", "rib", "chequier", "operation"],
        categories=["VIREMENT_PRELEVEMENT", "CHEQUE_EFFET"],
    ),
    DepartmentInfo(
        code="CREDITS", name="Credits et Financement",
        keywords=["credit", "pret", "echeance", "mainlevee", "operation"],
        categories=["CREDIT_FINANCEMENT"],
    ),
]


# ------------------------------------------------------------------- language
def test_arabic_script_is_detected_without_a_model():
    result = lid.detect(normalize(body="من ثلاثة أيام ما فماش شبكة في الحي"))
    assert result.code == "ar"
    assert result.source == "script"


def test_french_is_detected():
    result = lid.detect(
        normalize(body="Je vous ecris car mon releve est incorrect depuis deux mois")
    )
    assert result.code == "fr"


@pytest.mark.parametrize(
    "text",
    [
        "3andi mochkla fel compte, 7atta lyoum ma7alouhech, yezzi",
        "el fatoura mte3i hedha chhar 210 dinar w ana ma badeltech",
        "nhabet nsakker el compte, 3malt talab men jomaa",
    ],
)
def test_derja_is_labelled_ar_tn(text):
    """No off-the-shelf model has a derja label; this is our own decision."""
    assert lid.detect(normalize(body=text)).code == "ar-tn"


def test_french_is_not_swallowed_by_the_derja_rule():
    for text in [
        "Bonjour, mon releve de janvier est incorrect et personne ne repond",
        "Je souhaite cloturer mon compte et transferer mes avoirs",
    ]:
        assert lid.detect(normalize(body=text)).code == "fr"


def test_language_detection_never_raises_on_empty_text():
    assert lid.detect(normalize(body="")).code in {"fr", "en", "ar", "ar-tn", "other"}


# -------------------------------------------------------------------- lexicon
@pytest.mark.parametrize(
    "text,expected",
    [
        ("j'ai commande un chequier il y a un mois", "CHEQUE_EFFET"),
        ("le distributeur a debite sans aucun billet", "DAB_GAB"),
        ("des agios preleves sur mon compte", "FRAIS_COMMISSIONS"),
        ("ma demande d'allocation touristique est refusee", "OPERATIONS_INTERNATIONALES"),
    ],
)
def test_lexicon_categorises_on_decisive_terms(text, expected):
    assert classify(normalize(body=text).indexable).category == expected


def test_lexicon_abstains_rather_than_guessing():
    """Below the thresholds the classifier says so instead of inventing a label."""
    verdict = classify(normalize(body="bonjour j ai un probleme merci").indexable)
    assert verdict.category is None
    assert verdict.reason in {
        "no_signal", "insufficient_evidence", "evidence_too_spread",
        "margin_too_narrow",
    }


def test_the_verdict_carries_the_terms_that_produced_it():
    """Traceability is the point of the lexicon: never just a label."""
    verdict = classify(normalize(body="mon chequier n est jamais arrive").indexable)
    assert verdict.category == "CHEQUE_EFFET"
    assert "chequier" in verdict.evidence["CHEQUE_EFFET"]


def test_accented_french_classifies_like_its_bare_twin():
    accented = classify(normalize("Chèque rejeté à tort", "défaut de provision").indexable)
    bare = classify(normalize("Cheque rejete a tort", "defaut de provision").indexable)
    assert accented.category == bare.category is not None


# -------------------------------------------------------------------- routing
@pytest.mark.parametrize(
    "body,expected",
    [
        ("le distributeur a garde ma carte", "MONETIQUE"),
        ("mon virement n est pas arrive, le rib etait correct", "OPERATIONS"),
        ("l echeance de mon credit est prelevee deux fois", "CREDITS"),
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


def test_top_keywords_skips_short_words_and_placeholders():
    keywords = top_keywords("les agios agios sont <url> tres eleves eleves eleves")
    assert keywords[0] == "eleves"
    assert "<url>" not in keywords
    assert "les" not in keywords


# --------------------------------------------------------------------- engine
async def test_engine_routes_and_categorises():
    output = await LexiconTriageEngine().analyze(
        TriageInput(
            subject="Chequier non delivre",
            body="J'ai commande un chequier il y a un mois, il n'est jamais arrive.",
            departments=DEPARTMENTS,
        )
    )
    assert output.category == "CHEQUE_EFFET"
    assert output.department_code == "OPERATIONS"
    assert output.needs_human_triage is False


async def test_engine_asks_for_a_human_when_it_cannot_decide():
    output = await LexiconTriageEngine().analyze(
        TriageInput(subject="Bonjour", body="merci de me rappeler",
                    departments=DEPARTMENTS)
    )
    assert output.category is None
    assert output.needs_human_triage is True
    assert output.triage_reason


async def test_engine_records_stage_latencies():
    output = await LexiconTriageEngine().analyze(
        TriageInput(subject="x", body="des agios injustifies", departments=DEPARTMENTS)
    )
    assert [stage["name"] for stage in output.stages] == [
        "normalize", "language", "classify", "route"
    ]
    assert all("latency_ms" in stage for stage in output.stages)


async def test_engine_is_fast():
    output = await LexiconTriageEngine().analyze(
        TriageInput(
            subject="Agios anormaux",
            body="Des agios de 187 dinars ont ete preleves a tort " * 20,
            departments=DEPARTMENTS,
        )
    )
    assert output.latency_ms < 50


def test_engine_health_is_not_degraded():
    """There is no model to be missing, so there is no degraded state."""
    health = LexiconTriageEngine().health()
    assert health.ready is True
    assert health.degraded is False

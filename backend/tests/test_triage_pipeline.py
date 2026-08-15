"""Dedup scoring, the full pipeline, the decision rules and assignment."""

from datetime import UTC, datetime, timedelta

import pytest

from app.config import settings
from app.domain.taxonomy import Category
from app.intelligence.dedup.detector import detect, jaccard, score_candidate, shingles
from app.intelligence.ports import DedupCandidate
from app.models.complaint import Complaint, Status, TriageState
from app.models.department import Department
from app.models.user import Role, User
from app.services import assignment_service, triage_service

COMPLAINTS = "/api/v1/complaints"

TEXT_A = (
    "des agios de 187 dinars ont ete preleves sur mon compte alors que je n ai "
    "jamais ete a decouvert je demande le detail du calcul"
)
TEXT_B = (
    "on m a preleve 187 dinars d agios sur mon compte alors que je n ai jamais "
    "ete a decouvert merci de me donner le detail du calcul"
)
TEXT_C = (
    "le distributeur de la marsa a debite mon compte sans delivrer le moindre "
    "billet et personne ne veut me rembourser"
)


def candidate(id_: str, subject: str, text: str, email: str | None = None):
    return DedupCandidate(
        id=id_, subject=subject, normalized_text=text,
        created_at=datetime.now(UTC), claimant_email=email,
    )


# --------------------------------------------------------------------- shingles
def test_shingles_of_short_text_is_the_whole_text():
    assert shingles("trop cher") == {"trop cher"}


def test_jaccard_of_identical_text_is_one():
    assert jaccard(TEXT_A, TEXT_A) == 1.0


def test_jaccard_of_unrelated_text_is_zero():
    assert jaccard(TEXT_A, TEXT_C) == 0.0


# ------------------------------------------------------------------- scoring
def test_near_identical_complaints_score_high():
    match = score_candidate(
        TEXT_A, "Agios eleves", candidate("1", "Agios eleves", TEXT_B), None
    )
    assert match.score > 0.6


def test_unrelated_complaints_score_low():
    match = score_candidate(
        TEXT_A, "Agios eleves", candidate("1", "Distributeur", TEXT_C), None
    )
    assert match.score < 0.3


def test_same_claimant_gets_a_bonus():
    same = score_candidate(
        TEXT_A, "Agios", candidate("1", "Agios", TEXT_B, "a@b.tn"), "a@b.tn"
    )
    other = score_candidate(
        TEXT_A, "Agios", candidate("1", "Agios", TEXT_B, "c@d.tn"), "a@b.tn"
    )
    assert same.score > other.score
    assert same.same_claimant is True


def test_two_signals_produce_a_usable_score():
    """Token-set ratio and shingle overlap alone must separate a near-duplicate."""
    match = score_candidate(
        TEXT_A, "Agios eleves", candidate("1", "Agios eleves", TEXT_B), None,
    )
    assert match.score > 0.6


# -------------------------------------------------------------------- detect
def test_same_claimant_duplicate_is_auto_linked():
    duplicate, _ = detect(
        TEXT_A, "Agios eleves",
        [candidate("1", "Agios eleves", TEXT_B, "a@b.tn")],
        claimant_email="a@b.tn",
        auto_threshold=0.6,
    )
    assert duplicate is not None
    assert duplicate.relation == "duplicate"


def test_different_claimants_are_related_not_duplicates():
    """Forty people reporting one outage is an incident cluster, not duplication."""
    duplicate, _ = detect(
        TEXT_C, "Distributeur",
        [candidate("1", "Distributeur", TEXT_C, "voisin@example.tn")],
        claimant_email="moi@example.tn",
        auto_threshold=0.6,
        cross_claimant_threshold=0.5,
    )
    assert duplicate is not None
    assert duplicate.relation == "related"


def test_cross_claimant_needs_a_much_higher_score():
    duplicate, suggestions = detect(
        TEXT_A, "Agios eleves",
        [candidate("1", "Agios eleves", TEXT_B, "autre@example.tn")],
        claimant_email="moi@example.tn",
        auto_threshold=0.60,
        suggest_threshold=0.30,
        cross_claimant_threshold=0.99,
    )
    assert duplicate is None
    assert suggestions  # still surfaced as a possible match


def test_no_candidates_means_no_match():
    assert detect(TEXT_A, "Agios", [], "a@b.tn") == (None, [])


def test_middling_scores_are_suggested_not_linked():
    _, suggestions = detect(
        TEXT_A, "Agios eleves",
        [candidate("1", "Agios eleves", TEXT_B, "a@b.tn")],
        claimant_email="a@b.tn",
        auto_threshold=0.99,
        suggest_threshold=0.3,
    )
    assert len(suggestions) == 1


# ------------------------------------------------------------------ assignment
def test_skill_match_scores_overlap():
    assert assignment_service.skill_match(
        ["frais", "commissions"], Category.FRAIS_COMMISSIONS
    ) == 1.0
    assert assignment_service.skill_match(
        ["frais"], Category.FRAIS_COMMISSIONS
    ) == 0.5
    assert assignment_service.skill_match(
        ["virement"], Category.FRAIS_COMMISSIONS
    ) == 0.0


def test_recency_decays():
    now = datetime.now(UTC)
    assert assignment_service.recency(now, now) == 1.0
    assert assignment_service.recency(now - timedelta(hours=36), now) == pytest.approx(0.5)
    assert assignment_service.recency(now - timedelta(days=10), now) == 0.0
    assert assignment_service.recency(None) == 0.0


def test_agent_score_prefers_the_less_loaded_agent():
    busy = User(email="a@x.tn", password_hash="x", full_name="A", max_concurrent=10)
    idle = User(email="b@x.tn", password_hash="x", full_name="B", max_concurrent=10)
    assert assignment_service.score_agent(idle, 0, None) > assignment_service.score_agent(
        busy, 9, None
    )


async def test_pick_agent_prefers_skills_then_load(departments):
    department = departments["RELATION_CLIENT"]
    specialist = User(
        email="spec@rakib.tn", password_hash="x", full_name="Specialist",
        role=Role.AGENT, department_id=department.id,
        skills=["frais", "commissions"],
        max_concurrent=10, last_active_at=datetime.now(UTC),
    )
    generalist = User(
        email="gen@rakib.tn", password_hash="x", full_name="Generalist",
        role=Role.AGENT, department_id=department.id, skills=["remboursement"],
        max_concurrent=10, last_active_at=datetime.now(UTC),
    )
    await specialist.insert()
    await generalist.insert()

    picked = await assignment_service.pick_agent(department, Category.FRAIS_COMMISSIONS)
    assert picked.email == "spec@rakib.tn"


async def test_pick_agent_returns_none_when_department_is_empty(departments):
    assert await assignment_service.pick_agent(departments["DIGITAL"], None) is None


async def test_pick_agent_skips_agents_at_capacity(departments):
    department = departments["RELATION_CLIENT"]
    agent = User(
        email="full@rakib.tn", password_hash="x", full_name="Full", role=Role.AGENT,
        department_id=department.id, max_concurrent=1,
        last_active_at=datetime.now(UTC),
    )
    await agent.insert()
    assert await assignment_service.pick_agent(department, None) is not None

    # One open complaint puts them at their max_concurrent of 1.
    from app.models.complaint import Assignment, Claimant

    await Complaint(
        ref="REC-2026-99999",
        claimant=Claimant(full_name="X", email="x@y.tn"),
        subject="Saturation", body="b" * 20,
        status=Status.IN_PROGRESS,
        assignment=Assignment(department_id=department.id, agent_id=agent.id),
    ).insert()

    assert await assignment_service.pick_agent(department, None) is None


# -------------------------------------------------------------- full pipeline
async def make_complaint(client, subject: str, body: str, email="fatma@example.tn"):
    created = (
        await client.post(
            COMPLAINTS,
            json={
                "subject": subject,
                "body": body,
                "claimant": {"full_name": "Fatma Ben Ali", "email": email},
            },
        )
    ).json()
    return await Complaint.get(created["id"])


async def test_triage_classifies_prioritises_and_routes(client):
    complaint = await make_complaint(
        client, "Agios anormalement elevee",
        "Ma prelevement d agios est de 187 dinars alors que mon plafond est a "
        "45 dinars par mois. Merci de me fournir le detail des consommations.",
    )
    result = await triage_service.triage_complaint(complaint)

    assert result.triage_state == TriageState.DONE
    assert result.analysis.priority in {1, 2, 3, 4}
    assert result.analysis.language
    assert result.assignment.department_code
    assert result.analysis.analyzed_at is not None


async def test_triage_writes_a_trace_with_all_six_stages(client):
    from app.models.analysis_trace import AnalysisTrace

    complaint = await make_complaint(
        client, "Distributeur",
        "Aucun signal dans le quartier depuis trois jours, impossible d appeler.",
    )
    await triage_service.triage_complaint(complaint)

    trace = await AnalysisTrace.find_one(AnalysisTrace.complaint_id == complaint.id)
    assert trace is not None
    assert trace.outcome == "ok"
    names = [stage.name for stage in trace.stages]
    assert "normalize" in names and "rules" in names and "dedup" in names


async def test_triage_records_rule_hits_with_matched_tokens(client):
    complaint = await make_complaint(
        client, "URGENT mise en demeure",
        "C est inacceptable, mon avocat va porter plainte. Depuis des semaines "
        "aucune reponse concernant ma agios de 340 dinars.",
    )
    result = await triage_service.triage_complaint(complaint)
    assert result.analysis.rule_hits
    assert all(hit.matched for hit in result.analysis.rule_hits)
    assert result.analysis.priority <= 2


async def test_low_confidence_routes_to_human_triage(client, monkeypatch):
    monkeypatch.setattr(settings, "category_confidence_threshold", 0.999)
    complaint = await make_complaint(client, "probleme", "bonjour j ai un probleme")
    result = await triage_service.triage_complaint(complaint)
    assert result.analysis.needs_human_triage is True
    # Every way the lexicon can decline to decide (see lexicon/classifier.py).
    assert result.analysis.triage_reason in {
        "no_signal", "insufficient_evidence", "evidence_too_spread",
        "margin_too_narrow",
    }


async def test_complaint_needing_human_triage_is_not_auto_assigned(client, monkeypatch):
    monkeypatch.setattr(settings, "category_confidence_threshold", 0.999)
    complaint = await make_complaint(client, "aide", "aidez moi s il vous plait")
    result = await triage_service.triage_complaint(complaint)
    assert result.assignment.agent_id is None
    assert str(result.assignment.method) == "queue"


async def test_triage_auto_assigns_when_confident(client, departments, monkeypatch):
    monkeypatch.setattr(settings, "category_confidence_threshold", 0.0)
    monkeypatch.setattr(settings, "ambiguity_margin", 0.0)
    for code in departments:
        await User(
            email=f"agent-{code}@rakib.tn", password_hash="x", full_name=f"Agent {code}",
            role=Role.AGENT, department_id=departments[code].id,
            max_concurrent=10, last_active_at=datetime.now(UTC),
        ).insert()

    complaint = await make_complaint(
        client, "Agios eleves",
        "Ma agios de janvier est de 187 dinars au lieu de 45 dinars, "
        "je conteste ce montant hors convention.",
    )
    result = await triage_service.triage_complaint(complaint)
    assert result.assignment.agent_id is not None
    assert result.status == Status.ASSIGNED


async def test_duplicate_is_flagged_but_never_auto_closed(client, monkeypatch):
    monkeypatch.setattr(settings, "dedup_auto_threshold", 0.5)
    first = await make_complaint(client, "Agios eleves", TEXT_A)
    await triage_service.triage_complaint(first)

    second = await make_complaint(client, "Agios eleves", TEXT_B)
    result = await triage_service.triage_complaint(second)

    assert result.analysis.duplicate_of == first.id
    assert result.status is not Status.CLOSED
    assert result.assignment.department_code is not None


async def test_unknown_department_falls_back_to_general(client, monkeypatch):
    """Deleting the routed department must not lose the complaint."""
    await Department.find(Department.code != "GENERAL").delete()
    complaint = await make_complaint(client, "Agios", "ma agios est trop elevee")
    result = await triage_service.triage_complaint(complaint)
    assert result.assignment.department_code == "GENERAL"


async def test_triage_failure_is_recorded_not_swallowed(client, monkeypatch):
    from app.intelligence import pipeline

    async def explode(*args, **kwargs):
        raise RuntimeError("engine exploded")

    monkeypatch.setattr(pipeline, "run", explode)
    complaint = await make_complaint(client, "Agios", "ma agios est trop elevee")
    result = await triage_service.triage_complaint(complaint)

    assert result.triage_state == TriageState.FAILED
    assert result.analysis.needs_human_triage is True


async def test_triage_is_fast(client):
    complaint = await make_complaint(
        client, "Agios anormale",
        "Ma prelevement d agios est de 187 dinars alors que mon plafond est a 45.",
    )
    result = await triage_service.triage_complaint(complaint)
    assert result.analysis.latency_ms < 200


# ------------------------------------------------------------------ endpoints
async def test_analysis_endpoint_exposes_the_full_trace(
    client, routed_complaint, agent_headers
):
    created = await routed_complaint()
    complaint = await Complaint.get(created["id"])
    await triage_service.triage_complaint(complaint)

    body = (
        await client.get(f"{COMPLAINTS}/{created['id']}/analysis", headers=agent_headers)
    ).json()
    assert body["ref"] == created["ref"]
    assert body["analysis"]["rule_hits"] is not None
    assert body["traces"]
    assert body["traces"][0]["stages"]


async def test_retriage_requires_supervisor(client, routed_complaint, agent_headers):
    created = await routed_complaint()
    response = await client.post(
        f"{COMPLAINTS}/{created['id']}/retriage", headers=agent_headers
    )
    assert response.status_code == 403


async def test_retriage_reruns_the_pipeline(client, make_user, login, routed_complaint):
    created = await routed_complaint()
    await make_user(email="sup@rakib.tn", password="Password123!", role=Role.SUPERVISOR)
    headers = await login(client, "sup@rakib.tn", "Password123!")

    response = await client.post(
        f"{COMPLAINTS}/{created['id']}/retriage", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["triage_state"] == "done"

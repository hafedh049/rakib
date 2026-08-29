"""The triage flow end to end: analyse, route, record."""


from app.models.complaint import Complaint, Status, TriageState

COMPLAINTS = "/api/v1/complaints"

CHEQUE = {
    "subject": "Chequier non delivre",
    "body": "J'ai commande un chequier il y a un mois. Il n'est jamais arrive a "
            "l'agence et les frais ont pourtant ete preleves.",
    "claimant": {"full_name": "Fatma Ben Ali", "email": "fatma@example.tn"},
}
VAGUE = {
    "subject": "probleme",
    "body": "bonjour j ai un probleme merci de me rappeler",
    "claimant": {"full_name": "Anis Dridi", "email": "anis@example.tn"},
}


async def _create(client, payload) -> Complaint:
    """Create, then triage synchronously.

    In production the worker picks this up from the queue; here we run it
    inline so the assertions are about the analysis, not about timing.
    """
    from app.services import triage_service

    created = (await client.post(COMPLAINTS, json=payload)).json()
    complaint = await Complaint.get(created["id"])
    await triage_service.triage_complaint(complaint)
    return await Complaint.get(created["id"])


async def test_triage_categorises_and_routes(client):
    complaint = await _create(client, CHEQUE)
    assert complaint.analysis.category == "CHEQUE_EFFET"
    assert complaint.assignment.department_code == "OPERATIONS"
    assert complaint.triage_state is TriageState.DONE


async def test_triage_records_the_terms_that_decided(client):
    """The evidence is the explainability payload — never omit it."""
    complaint = await _create(client, CHEQUE)
    assert "chequier" in complaint.analysis.evidence["CHEQUE_EFFET"]


async def test_triage_writes_every_stage(client):
    complaint = await _create(client, CHEQUE)
    assert complaint.analysis.latency_ms is not None
    assert complaint.analysis.engine == "lexicon"
    assert complaint.analysis.analyzed_at is not None


async def test_an_undecidable_complaint_goes_to_a_human(client):
    complaint = await _create(client, VAGUE)
    assert complaint.analysis.category is None
    assert complaint.analysis.needs_human_triage is True
    assert complaint.analysis.triage_reason


async def test_a_complaint_lands_in_the_department_queue_not_on_an_agent(client):
    """Assigning the agent is the admin's decision, by design."""
    complaint = await _create(client, CHEQUE)
    assert complaint.assignment.agent_id is None
    assert complaint.status in {Status.NEW, Status.TRIAGED}


async def test_retriage_never_reopens_a_closed_complaint(client):
    from app.services import triage_service

    complaint = await _create(client, CHEQUE)
    complaint.status = Status.RESOLVED
    await complaint.save()

    await triage_service.retriage(complaint)
    refreshed = await Complaint.get(complaint.id)
    assert refreshed.status is Status.RESOLVED


async def test_triage_failure_is_recorded_not_swallowed(client, monkeypatch):
    """A broken analysis must never lose the complaint itself."""
    from app.services import triage, triage_service

    class Broken:
        name = "broken"

        async def analyze(self, data):
            raise RuntimeError("boom")

    monkeypatch.setattr(triage, "get_engine", lambda: Broken())
    complaint = await _create(client, VAGUE)
    complaint.triage_state = TriageState.PENDING
    await triage_service.triage_complaint(complaint)

    refreshed = await Complaint.get(complaint.id)
    assert refreshed.triage_state is TriageState.FAILED
    assert refreshed.subject == VAGUE["subject"]


async def test_analysis_endpoint_exposes_the_trace(client, make_user, login):
    """A supervisor, not the seeded agent: this complaint routes to OPERATIONS
    and the department scope correctly hides it from an agent elsewhere."""
    from app.models.user import Role

    await make_user(email="sup@rakib.tn", password="Password123!", role=Role.SUPERVISOR)
    headers = await login(client, "sup@rakib.tn", "Password123!")

    complaint = await _create(client, CHEQUE)
    body = (
        await client.get(f"{COMPLAINTS}/{complaint.id}/analysis", headers=headers)
    ).json()
    assert body["category"] == "CHEQUE_EFFET"
    assert body["analysis"]["evidence"]["CHEQUE_EFFET"]

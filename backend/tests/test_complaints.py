"""Complaint lifecycle, RBAC scoping, and the anti-enumeration guarantee."""

import re

import pytest

from app.domain.taxonomy import Category
from app.models.complaint import Complaint, Status
from app.models.user import Role

COMPLAINTS = "/api/v1/complaints"
TRACK = "/api/v1/complaints/track"

BODY = (
    "Ma facture de janvier s'eleve a 187 dinars alors que mon forfait est a 45 dinars. "
    "Merci de me fournir le detail des consommations."
)


@pytest.fixture
async def agent_headers(client, make_user, login, departments):
    """An agent who actually belongs to a department, as in production."""
    await make_user(
        email="agent@rakib.tn", password="Password123!", role=Role.AGENT,
        department_id=departments["FACTURATION"].id,
    )
    return await login(client, "agent@rakib.tn", "Password123!")


@pytest.fixture
def routed_complaint(client):
    """Create a complaint and route it, the way the triage worker will."""

    async def _create(category: str = Category.FACTURATION) -> dict:
        from app.services import complaint_service

        created = (await client.post(COMPLAINTS, json=payload())).json()
        complaint = await Complaint.get(created["id"])
        complaint.analysis.category = category
        await complaint_service.route_to_category_department(complaint, category)
        await complaint.save()
        return created

    return _create


def payload(**overrides):
    base = {
        "subject": "Facture anormalement elevee",
        "body": BODY,
        "channel": "web",
        "claimant": {
            "full_name": "Fatma Ben Ali",
            "email": "fatma@example.tn",
            "phone": "20 145 879",
        },
    }
    base.update(overrides)
    return base


# ------------------------------------------------------------------------- creation
async def test_anonymous_submission_returns_ref_and_tracking_url(client):
    response = await client.post(COMPLAINTS, json=payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert re.fullmatch(r"REC-\d{4}-\d{5}", body["ref"])
    assert "token=" in body["tracking_url"]
    assert body["status"] == Status.NEW


async def test_phone_only_submission_is_accepted(client):
    """Many Tunisian claimants have no email — phone alone must work."""
    response = await client.post(
        COMPLAINTS,
        json=payload(claimant={"full_name": "Leila Nasri", "phone": "22336698"}),
    )
    assert response.status_code == 201
    complaint = await Complaint.find_one(Complaint.ref == response.json()["ref"])
    assert complaint.claimant.phone == "+21622336698"
    assert complaint.claimant.email is None


async def test_submission_without_email_or_phone_is_rejected(client):
    response = await client.post(
        COMPLAINTS, json=payload(claimant={"full_name": "Anonyme"})
    )
    assert response.status_code == 422


async def test_refs_are_unique_and_sequential(client):
    refs = [
        (await client.post(COMPLAINTS, json=payload())).json()["ref"] for _ in range(3)
    ]
    assert len(set(refs)) == 3
    numbers = [int(ref.split("-")[-1]) for ref in refs]
    assert numbers == sorted(numbers)


async def test_authenticated_claimant_submission_is_linked_to_the_account(
    client, make_user, login
):
    user = await make_user(
        email="claimant@example.tn", password="Password123!", role=Role.CLAIMANT
    )
    headers = await login(client, "claimant@example.tn", "Password123!")
    response = await client.post(COMPLAINTS, json=payload(), headers=headers)

    complaint = await Complaint.find_one(Complaint.ref == response.json()["ref"])
    assert complaint.claimant.user_id == user.id


async def test_creation_writes_a_timeline_entry(client):
    response = await client.post(COMPLAINTS, json=payload())
    complaint = await Complaint.find_one(Complaint.ref == response.json()["ref"])
    assert [entry.action for entry in complaint.timeline] == ["complaint.created"]


async def test_creation_sets_a_provisional_sla(client):
    response = await client.post(COMPLAINTS, json=payload())
    complaint = await Complaint.find_one(Complaint.ref == response.json()["ref"])
    assert complaint.sla.due_at is not None
    assert complaint.triage_state == "pending"


# ----------------------------------------------------------- anti-enumeration story
async def test_tracking_token_grants_access_to_its_own_complaint(client):
    created = (await client.post(COMPLAINTS, json=payload())).json()
    token = created["tracking_url"].split("token=")[1]

    response = await client.get(TRACK, params={"token": token})
    assert response.status_code == 200
    assert response.json()["ref"] == created["ref"]


async def test_a_tracking_token_cannot_read_another_complaint(client):
    first = (await client.post(COMPLAINTS, json=payload())).json()
    await client.post(COMPLAINTS, json=payload())

    token = first["tracking_url"].split("token=")[1]
    assert (await client.get(TRACK, params={"token": token})).json()["ref"] == first["ref"]


@pytest.mark.parametrize("token", ["", "garbage", "a.b.c.d"])
async def test_invalid_tracking_tokens_are_rejected(client, token):
    assert (await client.get(TRACK, params={"token": token})).status_code in (401, 422)


async def test_there_is_no_endpoint_that_reads_a_complaint_by_ref(client):
    """The ref is sequential; if it could fetch a complaint the whole system
    would be enumerable. Guard against anyone reintroducing such a route."""
    created = (await client.post(COMPLAINTS, json=payload())).json()
    for path in (f"{COMPLAINTS}/{created['ref']}", f"{COMPLAINTS}/ref/{created['ref']}"):
        assert (await client.get(path)).status_code in (401, 404, 422)


async def test_public_view_hides_internal_notes(client, routed_complaint, agent_headers):
    created = await routed_complaint()
    headers = agent_headers

    await client.post(
        f"{COMPLAINTS}/{created['id']}/messages",
        json={"body": "Client a rappeler, dossier sensible", "internal": True},
        headers=headers,
    )
    await client.post(
        f"{COMPLAINTS}/{created['id']}/messages",
        json={"body": "Nous traitons votre demande.", "internal": False},
        headers=headers,
    )

    token = created["tracking_url"].split("token=")[1]
    public = (await client.get(TRACK, params={"token": token})).json()
    bodies = [m["body"] for m in public["messages"]]
    assert "Nous traitons votre demande." in bodies
    assert all("dossier sensible" not in b for b in bodies)


# ------------------------------------------------------------------- listing / RBAC
async def test_listing_requires_authentication(client):
    assert (await client.get(COMPLAINTS)).status_code == 401


async def test_claimant_only_sees_their_own_complaints(client, make_user, login):
    await make_user(email="a@example.tn", password="Password123!", role=Role.CLAIMANT)
    headers_a = await login(client, "a@example.tn", "Password123!")
    await client.post(COMPLAINTS, json=payload(), headers=headers_a)
    await client.post(COMPLAINTS, json=payload())  # anonymous, someone else

    listing = (await client.get(COMPLAINTS, headers=headers_a)).json()
    assert len(listing["items"]) == 1


async def test_agent_sees_their_department_queue(
    client, make_user, login, departments
):
    await make_user(
        email="agent@rakib.tn", password="Password123!", role=Role.AGENT,
        department_id=departments["FACTURATION"].id,
    )
    headers = await login(client, "agent@rakib.tn", "Password123!")

    created = (await client.post(COMPLAINTS, json=payload())).json()
    complaint = await Complaint.get(created["id"])
    from app.services import complaint_service

    await complaint_service.route_to_category_department(
        complaint, Category.FACTURATION
    )
    await complaint.save()

    listing = (await client.get(COMPLAINTS, headers=headers)).json()
    assert [item["ref"] for item in listing["items"]] == [created["ref"]]


async def test_untriaged_complaints_belong_to_supervisors_not_agents(
    client, make_user, login, agent_headers
):
    """A complaint with no department yet is in the triage queue, which is a
    supervisor surface. Agents work their department's queue, not the raw inbox."""
    await client.post(COMPLAINTS, json=payload())  # never routed

    agent_view = (await client.get(COMPLAINTS, headers=agent_headers)).json()
    assert agent_view["items"] == []

    await make_user(email="sup@rakib.tn", password="Password123!", role=Role.SUPERVISOR)
    sup_headers = await login(client, "sup@rakib.tn", "Password123!")
    sup_view = (await client.get(COMPLAINTS, headers=sup_headers)).json()
    assert len(sup_view["items"]) == 1


async def test_supervisor_sees_everything(client, make_user, login):
    await make_user(email="sup@rakib.tn", password="Password123!", role=Role.SUPERVISOR)
    headers = await login(client, "sup@rakib.tn", "Password123!")
    for _ in range(3):
        await client.post(COMPLAINTS, json=payload())

    listing = (await client.get(COMPLAINTS, headers=headers)).json()
    assert len(listing["items"]) == 3


async def test_cursor_pagination_walks_every_row_once(client, make_user, login):
    await make_user(email="sup@rakib.tn", password="Password123!", role=Role.SUPERVISOR)
    headers = await login(client, "sup@rakib.tn", "Password123!")
    for _ in range(7):
        await client.post(COMPLAINTS, json=payload())

    seen: list[str] = []
    cursor = None
    for _ in range(10):
        params = {"limit": 3}
        if cursor:
            params["cursor"] = cursor
        page = (await client.get(COMPLAINTS, params=params, headers=headers)).json()
        seen.extend(item["ref"] for item in page["items"])
        cursor = page["next_cursor"]
        if not cursor:
            break

    assert len(seen) == 7
    assert len(set(seen)) == 7


async def test_bad_cursor_is_a_validation_error(client, make_user, login):
    await make_user(email="sup@rakib.tn", password="Password123!", role=Role.SUPERVISOR)
    headers = await login(client, "sup@rakib.tn", "Password123!")
    response = await client.get(
        COMPLAINTS, params={"cursor": "!!!not-base64!!!"}, headers=headers
    )
    assert response.status_code == 422


# ------------------------------------------------------------------------ mutations
async def test_agent_correcting_the_category_flags_a_training_signal(
    client, routed_complaint, agent_headers
):
    created = await routed_complaint()
    response = await client.patch(
        f"{COMPLAINTS}/{created['id']}",
        json={"category": Category.PAIEMENT_RECHARGE},
        headers=agent_headers,
    )
    assert response.status_code == 200
    assert response.json()["corrected"] is True


async def test_unknown_category_is_rejected(client, routed_complaint, agent_headers):
    created = await routed_complaint()
    response = await client.patch(
        f"{COMPLAINTS}/{created['id']}", json={"category": "PIZZA"},
        headers=agent_headers,
    )
    assert response.status_code == 422


async def test_agent_cannot_change_priority(client, routed_complaint, agent_headers):
    created = await routed_complaint()
    response = await client.patch(
        f"{COMPLAINTS}/{created['id']}", json={"priority": 1}, headers=agent_headers
    )
    assert response.status_code == 403


async def test_supervisor_changing_priority_recomputes_the_sla(
    client, make_user, login
):
    created = (await client.post(COMPLAINTS, json=payload())).json()
    await make_user(email="sup@rakib.tn", password="Password123!", role=Role.SUPERVISOR)
    headers = await login(client, "sup@rakib.tn", "Password123!")

    await client.patch(
        f"{COMPLAINTS}/{created['id']}", json={"priority": 1}, headers=headers
    )
    complaint = await Complaint.get(created["id"])
    assert complaint.analysis.priority == 1
    assert complaint.sla.hours == 4  # SLA_HOURS_P1


async def test_claimant_cannot_patch_a_complaint(client, make_user, login):
    await make_user(email="c@example.tn", password="Password123!", role=Role.CLAIMANT)
    headers = await login(client, "c@example.tn", "Password123!")
    created = (await client.post(COMPLAINTS, json=payload(), headers=headers)).json()

    response = await client.patch(
        f"{COMPLAINTS}/{created['id']}", json={"status": "closed"}, headers=headers
    )
    assert response.status_code == 403


async def test_claimant_cannot_post_an_internal_note(client, make_user, login):
    await make_user(email="c@example.tn", password="Password123!", role=Role.CLAIMANT)
    headers = await login(client, "c@example.tn", "Password123!")
    created = (await client.post(COMPLAINTS, json=payload(), headers=headers)).json()

    response = await client.post(
        f"{COMPLAINTS}/{created['id']}/messages",
        json={"body": "note", "internal": True},
        headers=headers,
    )
    assert response.status_code == 403


async def test_out_of_scope_complaint_is_404_not_403(client, make_user, login):
    """Scope violations must be indistinguishable from non-existent rows."""
    created = (await client.post(COMPLAINTS, json=payload())).json()
    await make_user(email="c@example.tn", password="Password123!", role=Role.CLAIMANT)
    headers = await login(client, "c@example.tn", "Password123!")

    response = await client.get(f"{COMPLAINTS}/{created['id']}", headers=headers)
    assert response.status_code == 404


# ---------------------------------------------------------- resolution/satisfaction
async def test_resolve_then_satisfaction(client, routed_complaint, agent_headers):
    created = await routed_complaint()
    resolved = await client.post(
        f"{COMPLAINTS}/{created['id']}/resolve",
        json={"resolution": "Avoir de 142 dinars emis sur la prochaine facture."},
        headers=agent_headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == Status.RESOLVED

    from app.core.security import create_tracking_token

    token = create_tracking_token(created["id"], scope="satisfaction")
    response = await client.post(
        "/api/v1/complaints/satisfaction",
        params={"token": token},
        json={"score": 4, "comment": "Reglé rapidement"},
    )
    assert response.status_code == 200
    assert response.json()["satisfaction_submitted"] is True


async def test_satisfaction_is_refused_before_resolution(client):
    created = (await client.post(COMPLAINTS, json=payload())).json()
    from app.core.security import create_tracking_token

    token = create_tracking_token(created["id"], scope="satisfaction")
    response = await client.post(
        "/api/v1/complaints/satisfaction", params={"token": token}, json={"score": 5}
    )
    assert response.status_code == 409


async def test_satisfaction_cannot_be_submitted_twice(
    client, routed_complaint, agent_headers
):
    created = await routed_complaint()
    await client.post(
        f"{COMPLAINTS}/{created['id']}/resolve",
        json={"resolution": "Traite."},
        headers=agent_headers,
    )

    from app.core.security import create_tracking_token

    token = create_tracking_token(created["id"], scope="satisfaction")
    first = await client.post(
        "/api/v1/complaints/satisfaction", params={"token": token}, json={"score": 5}
    )
    second = await client.post(
        "/api/v1/complaints/satisfaction", params={"token": token}, json={"score": 1}
    )
    assert first.status_code == 200
    assert second.status_code == 409

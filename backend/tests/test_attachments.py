"""Attachment upload, including the anonymous token path.

Anonymous submission is the common case in Tunisia, and a photo of the disputed
bill is the most useful evidence a claimant can send — so the token path is a
first-class route, not a convenience.
"""

import pytest

from app.core.security import create_tracking_token
from app.models.complaint import Complaint
from app.models.user import Role
from app.services import storage

COMPLAINTS = "/api/v1/complaints"

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch):
    """MinIO is not part of the test stack; the API contract is what matters."""
    stored: dict[str, bytes] = {}

    async def put_object(key: str, data: bytes, content_type: str) -> None:
        stored[key] = data

    async def presigned_url(key: str, expires_in: int = 900) -> str:
        return f"https://minio.test/{key}?sig=fake"

    monkeypatch.setattr(storage, "put_object", put_object)
    monkeypatch.setattr(storage, "presigned_url", presigned_url)
    return stored


async def create_anonymous(client) -> dict:
    return (
        await client.post(
            COMPLAINTS,
            json={
                "subject": "Facture contestee",
                "body": "Le montant facture ne correspond pas a mon forfait mensuel.",
                "claimant": {"full_name": "Fatma Ben Ali", "phone": "20145879"},
            },
        )
    ).json()


def upload(client, complaint_id: str, *, token: str | None = None, headers=None):
    params = {"token": token} if token else None
    return client.post(
        f"{COMPLAINTS}/{complaint_id}/attachments",
        params=params,
        headers=headers or {},
        files={"file": ("facture.png", PNG, "image/png")},
    )


# --------------------------------------------------------------- token path
async def test_anonymous_claimant_can_attach_with_their_token(client, fake_storage):
    created = await create_anonymous(client)
    token = created["tracking_url"].split("token=")[1]

    response = await upload(client, created["id"], token=token)
    assert response.status_code == 201, response.text
    assert len(response.json()["attachments"]) == 1
    assert fake_storage


async def test_upload_without_token_or_session_is_refused(client):
    created = await create_anonymous(client)
    assert (await upload(client, created["id"])).status_code == 401


async def test_a_token_cannot_attach_to_another_complaint(client):
    """The token is scoped to exactly one complaint and grants nothing else."""
    first = await create_anonymous(client)
    second = await create_anonymous(client)
    token = first["tracking_url"].split("token=")[1]

    assert (await upload(client, second["id"], token=token)).status_code == 404


async def test_a_forged_token_is_refused(client):
    created = await create_anonymous(client)
    assert (
        await upload(client, created["id"], token="not-a-real-token")
    ).status_code == 401


async def test_satisfaction_token_cannot_be_used_to_attach(client):
    """Scope separation holds here too."""
    created = await create_anonymous(client)
    token = create_tracking_token(created["id"], scope="satisfaction")
    assert (await upload(client, created["id"], token=token)).status_code == 401


# -------------------------------------------------------------- staff path
async def test_agent_can_attach_to_a_complaint_in_scope(
    client, routed_complaint, agent_headers, fake_storage
):
    created = await routed_complaint()
    response = await upload(client, created["id"], headers=agent_headers)
    assert response.status_code == 201


async def test_claimant_cannot_attach_to_someone_elses_complaint(
    client, make_user, login
):
    created = await create_anonymous(client)
    await make_user(email="other@example.tn", password="Password123!",
                    role=Role.CLAIMANT)
    headers = await login(client, "other@example.tn", "Password123!")
    assert (await upload(client, created["id"], headers=headers)).status_code == 404


# ------------------------------------------------------------- validation
async def test_disallowed_content_type_is_rejected(client):
    created = await create_anonymous(client)
    token = created["tracking_url"].split("token=")[1]

    response = await client.post(
        f"{COMPLAINTS}/{created['id']}/attachments",
        params={"token": token},
        files={"file": ("payload.exe", b"MZ\x90\x00", "application/x-msdownload")},
    )
    assert response.status_code == 422


async def test_oversized_file_is_rejected(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_attachment_mb", 0)
    created = await create_anonymous(client)
    token = created["tracking_url"].split("token=")[1]

    assert (await upload(client, created["id"], token=token)).status_code == 422


async def test_upload_is_recorded_on_the_timeline(client, fake_storage):
    created = await create_anonymous(client)
    token = created["tracking_url"].split("token=")[1]
    await upload(client, created["id"], token=token)

    complaint = await Complaint.get(created["id"])
    assert any(entry.action == "attachment.added" for entry in complaint.timeline)


# --------------------------------------------------------------- download
async def test_presigned_url_is_handed_out_to_the_token_holder(client, fake_storage):
    created = await create_anonymous(client)
    token = created["tracking_url"].split("token=")[1]
    uploaded = (await upload(client, created["id"], token=token)).json()
    attachment_id = uploaded["attachments"][0]["id"]

    response = await client.get(
        f"{COMPLAINTS}/{created['id']}/attachments/{attachment_id}",
        params={"token": token},
    )
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://minio.test/")


async def test_unknown_attachment_is_404(client):
    created = await create_anonymous(client)
    token = created["tracking_url"].split("token=")[1]
    response = await client.get(
        f"{COMPLAINTS}/{created['id']}/attachments/does-not-exist",
        params={"token": token},
    )
    assert response.status_code == 404


# ------------------------------------------------------- concurrency regression
async def test_attachment_survives_a_concurrent_triage(client, fake_storage):
    """Triage must not wipe an attachment uploaded while it was running.

    The original bug: the worker fetched the complaint, the claimant uploaded a
    file, then the worker wrote the whole document back from its stale copy —
    silently discarding both the attachment and its timeline entry.
    """
    from app.services import triage_service

    created = await create_anonymous(client)
    token = created["tracking_url"].split("token=")[1]

    # The worker's view of the complaint, taken BEFORE the upload.
    stale = await Complaint.get(created["id"])

    await upload(client, created["id"], token=token)

    # Triage now completes against that stale in-memory copy.
    await triage_service.triage_complaint(stale)

    persisted = await Complaint.get(created["id"])
    assert len(persisted.attachments) == 1, "triage clobbered the attachment"
    assert any(e.action == "attachment.added" for e in persisted.timeline)
    assert any(e.action == "triage.completed" for e in persisted.timeline)
    assert persisted.analysis.analyzed_at is not None


async def test_message_survives_a_concurrent_triage(
    client, routed_complaint, agent_headers
):
    from app.services import triage_service

    created = await routed_complaint()
    stale = await Complaint.get(created["id"])

    await client.post(
        f"{COMPLAINTS}/{created['id']}/messages",
        json={"body": "Nous avons bien recu votre dossier.", "internal": False},
        headers=agent_headers,
    )
    await triage_service.triage_complaint(stale)

    persisted = await Complaint.get(created["id"])
    assert len(persisted.messages) == 1, "triage clobbered the reply"

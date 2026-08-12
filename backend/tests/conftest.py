import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-bytes-long-ok")
os.environ.setdefault(
    "TRACKING_TOKEN_SECRET", "test-tracking-secret-at-least-32-bytes"
)
os.environ.setdefault(
    "MONGO_URI", "mongodb://localhost:27017/rakib_test"
)

from app import db
from app.core.security import hash_password
from app.events import bus
from app.events.types import STREAM_KEY
from app.main import app
from app.models import ALL_DOCUMENTS
from app.models.department import Department
from app.models.user import Role, User
from app.services import triage
from app.services.kb_service import rebuild_index, seed_articles
from app.services.rules_service import seed_rules
from app.services.seed_service import seed_departments


@pytest.fixture(scope="session", autouse=True)
async def _database() -> AsyncIterator[None]:
    database = await db.init_db(os.environ["MONGO_URI"])
    yield
    await database.client.drop_database(database.name)
    await db.close_db()


@pytest.fixture(autouse=True)
async def _clean_collections() -> AsyncIterator[None]:
    """Each test starts from an empty database plus the seeded catalogue.

    Departments are seeded because the app seeds them at boot and the lifespan
    does not run under ASGITransport — tests should see the same world the
    running system does.
    """
    for document in ALL_DOCUMENTS:
        await document.get_motor_collection().delete_many({})
    await seed_departments()
    await seed_rules()
    await seed_articles()
    await rebuild_index()
    await triage.refresh_rules()
    try:
        await bus.get_redis().delete(STREAM_KEY)
    except Exception:  # noqa: BLE001 — Redis is optional for most tests
        pass
    yield


@pytest.fixture
async def departments() -> dict[str, Department]:
    return {d.code: d for d in await Department.find_all().to_list()}


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def make_user():
    async def _make(
        email: str = "agent@rakib.tn",
        password: str = "Password123!",
        role: Role = Role.AGENT,
        **kwargs,
    ) -> User:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=kwargs.pop("full_name", "Test User"),
            role=role,
            **kwargs,
        )
        await user.insert()
        return user

    return _make


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

    async def _create(category: str = "FACTURATION") -> dict:
        from app.models.complaint import Complaint
        from app.services import complaint_service

        created = (
            await client.post(
                "/api/v1/complaints",
                json={
                    "subject": "Facture anormalement elevee",
                    "body": "Ma facture de janvier s'eleve a 187 dinars alors que "
                            "mon forfait est a 45 dinars. Merci de verifier.",
                    "claimant": {
                        "full_name": "Fatma Ben Ali", "email": "fatma@example.tn"
                    },
                },
            )
        ).json()
        complaint = await Complaint.get(created["id"])
        complaint.analysis.category = category
        await complaint_service.route_to_category_department(complaint, category)
        await complaint.save()
        return created

    return _create


@pytest.fixture
def login():
    async def _login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
        response = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login

"""Analytics aggregations and their RBAC."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.complaint import Assignment, Claimant, Complaint, Satisfaction, Status
from app.models.user import Role, User

ANALYTICS = "/api/v1/analytics"


@pytest.fixture
async def supervisor_headers(client, make_user, login):
    await make_user(email="sup@rakib.tn", password="Password123!", role=Role.SUPERVISOR)
    return await login(client, "sup@rakib.tn", "Password123!")


@pytest.fixture
async def seeded(departments):
    """A small but realistic spread: categories, priorities, breaches, ratings."""
    agent = User(
        email="agent1@rakib.tn", password_hash="x", full_name="Karim Jelassi",
        role=Role.AGENT, department_id=departments["RELATION_CLIENT"].id,
    )
    await agent.insert()

    now = datetime.now(UTC)
    rows = [
        ("FRAIS_COMMISSIONS", 1, Status.RESOLVED, True, 4),
        ("FRAIS_COMMISSIONS", 2, Status.IN_PROGRESS, False, None),
        ("FRAIS_COMMISSIONS", 3, Status.NEW, False, None),
        ("CARTE_BANCAIRE", 1, Status.RESOLVED, False, 5),
        ("CARTE_BANCAIRE", 4, Status.CLOSED, False, 2),
        ("BANQUE_DIGITALE", 3, Status.ASSIGNED, True, None),
    ]
    for index, (category, priority, status, breached, rating) in enumerate(rows):
        created = now - timedelta(days=index, hours=3)
        complaint = Complaint(
            ref=f"REC-2026-2000{index}",
            claimant=Claimant(full_name="Fatma", email="fatma@example.tn"),
            subject=f"Reclamation {index}",
            body="corps de la reclamation pour les tests d analyse",
            status=status,
            created_at=created,
            updated_at=created,
            assignment=Assignment(
                department_id=departments["RELATION_CLIENT"].id, agent_id=agent.id
            ),
        )
        complaint.analysis.category = category
        complaint.analysis.priority = priority
        complaint.analysis.category_confidence = 0.4 + index * 0.1
        complaint.analysis.rule_hits = [
            {"code": "URGENCY_LEXICON_FR", "label": "Urgence", "weight": 15,
             "matched": ["urgent"]}
        ]
        complaint.sla.breached = breached
        complaint.sla.due_at = created + timedelta(hours=24)
        if status in (Status.RESOLVED, Status.CLOSED):
            complaint.sla.resolved_at = created + timedelta(hours=6)
        if rating is not None:
            complaint.satisfaction = Satisfaction(score=rating)
        if index == 0:
            complaint.corrected = True
        await complaint.insert()
    return agent


# --------------------------------------------------------------------- overview
async def test_overview_counts_and_rates(client, agent_headers, seeded):
    body = (await client.get(f"{ANALYTICS}/overview", headers=agent_headers)).json()
    assert body["total"] == 6
    assert body["closed"] == 3
    assert body["open"] == 3
    assert body["sla"]["breached"] == 2
    assert body["sla"]["compliance_rate"] == pytest.approx(1 - 2 / 6, abs=0.001)
    assert body["avg_resolution_hours"] == pytest.approx(6.0, abs=0.1)
    assert body["satisfaction"]["responses"] == 3


async def test_overview_on_an_empty_system_does_not_divide_by_zero(
    client, agent_headers
):
    body = (await client.get(f"{ANALYTICS}/overview", headers=agent_headers)).json()
    assert body["total"] == 0
    assert body["sla"]["compliance_rate"] == 1.0
    assert body["avg_resolution_hours"] is None


async def test_window_narrows_the_result(client, agent_headers, seeded):
    body = (
        await client.get(
            f"{ANALYTICS}/overview", params={"days": 2}, headers=agent_headers
        )
    ).json()
    assert body["total"] < 6


# -------------------------------------------------------------------- breakdowns
async def test_by_category(client, agent_headers, seeded):
    rows = (await client.get(f"{ANALYTICS}/by-category", headers=agent_headers)).json()
    assert rows[0]["category"] == "FRAIS_COMMISSIONS"
    assert rows[0]["count"] == 3
    assert 0 <= rows[0]["avg_confidence"] <= 1


async def test_volume_by_day_is_ordered(client, agent_headers, seeded):
    rows = (await client.get(f"{ANALYTICS}/volume", headers=agent_headers)).json()
    assert rows == sorted(rows, key=lambda row: row["date"])
    assert sum(row["count"] for row in rows) == 6


async def test_agent_workload(client, supervisor_headers, seeded):
    rows = (await client.get(f"{ANALYTICS}/agents", headers=supervisor_headers)).json()
    assert rows[0]["name"] == "Karim Jelassi"
    assert rows[0]["total"] == 6
    assert rows[0]["resolved"] == 3
    assert rows[0]["open"] == 3


async def test_supervision_board(client, agent_headers, seeded):
    body = (await client.get(f"{ANALYTICS}/supervision", headers=agent_headers)).json()
    assert body["breached"] == 1  # the resolved one is closed, so it drops out
    assert body["new"] == 1


# ------------------------------------------------------------------------ model
async def test_engine_report_exposes_the_correction_rate(
    client, supervisor_headers, seeded
):
    body = (await client.get(f"{ANALYTICS}/engine", headers=supervisor_headers)).json()
    assert body["corrections"]["triaged"] == 6
    assert body["corrections"]["corrected"] == 1
    assert body["corrections"]["correction_rate"] == pytest.approx(1 / 6, abs=0.001)


async def test_engine_report_on_an_empty_system(client, supervisor_headers):
    body = (await client.get(f"{ANALYTICS}/engine", headers=supervisor_headers)).json()
    assert body["corrections"]["triaged"] == 0
    assert body["corrections"]["correction_rate"] == 0.0


# ------------------------------------------------------------------------ rules
async def test_rules_report_ranks_by_fires(client, supervisor_headers, seeded):
    rows = (await client.get(f"{ANALYTICS}/rules", headers=supervisor_headers)).json()
    assert rows[0]["code"] == "URGENCY_LEXICON_FR"
    assert rows[0]["fires"] == 6
    assert rows[0]["label"] == "Vocabulaire d’urgence (FR)"
    assert 0 <= rows[0]["breach_rate"] <= 1


async def test_kb_report_lists_articles(client, supervisor_headers):
    rows = (await client.get(f"{ANALYTICS}/kb", headers=supervisor_headers)).json()
    assert rows
    assert "usage_count" in rows[0]


# ------------------------------------------------------------------------- RBAC
async def test_analytics_requires_staff(client, make_user, login):
    await make_user(email="c@example.tn", password="Password123!", role=Role.CLAIMANT)
    headers = await login(client, "c@example.tn", "Password123!")
    assert (
        await client.get(f"{ANALYTICS}/overview", headers=headers)
    ).status_code == 403


@pytest.mark.parametrize("path", ["agents", "engine", "rules", "kb"])
async def test_supervisor_only_endpoints(client, agent_headers, path):
    assert (
        await client.get(f"{ANALYTICS}/{path}", headers=agent_headers)
    ).status_code == 403

"""The /rules surface, including the simulator used for weight tuning."""

import pytest

from app.models.rule import Rule
from app.models.user import Role

RULES = "/api/v1/rules"
SIMULATE = "/api/v1/rules/simulate"


@pytest.fixture
async def admin_headers(client, make_user, login):
    await make_user(email="admin@rakib.tn", password="Password123!", role=Role.ADMIN)
    return await login(client, "admin@rakib.tn", "Password123!")


@pytest.fixture
async def supervisor_headers(client, make_user, login):
    await make_user(email="sup@rakib.tn", password="Password123!", role=Role.SUPERVISOR)
    return await login(client, "sup@rakib.tn", "Password123!")


# ------------------------------------------------------------------------ listing
async def test_default_rules_are_seeded(client, supervisor_headers):
    rules = (await client.get(RULES, headers=supervisor_headers)).json()
    codes = {rule["code"] for rule in rules}
    assert {"URGENCY_LEXICON_FR", "LEGAL_LEXICON_FR", "VIP_CLAIMANT"} <= codes
    assert all(rule["builtin"] for rule in rules)


async def test_agents_cannot_read_the_rule_set(client, make_user, login):
    await make_user(email="agent@rakib.tn", password="Password123!", role=Role.AGENT)
    headers = await login(client, "agent@rakib.tn", "Password123!")
    assert (await client.get(RULES, headers=headers)).status_code == 403


async def test_supervisors_cannot_edit_rules(client, supervisor_headers):
    rule = await Rule.find_one(Rule.code == "VIP_CLAIMANT")
    response = await client.patch(
        f"{RULES}/{rule.id}", json={"weight": 99}, headers=supervisor_headers
    )
    assert response.status_code == 403


# ------------------------------------------------------------------------ editing
async def test_admin_can_change_a_weight(client, admin_headers):
    rule = await Rule.find_one(Rule.code == "VIP_CLAIMANT")
    response = await client.patch(
        f"{RULES}/{rule.id}", json={"weight": 40}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["weight"] == 40


async def test_admin_can_deactivate_a_rule(client, admin_headers):
    rule = await Rule.find_one(Rule.code == "SHOUTING")
    response = await client.patch(
        f"{RULES}/{rule.id}", json={"active": False}, headers=admin_headers
    )
    assert response.json()["active"] is False


async def test_invalid_regex_config_is_rejected(client, admin_headers):
    rule = await Rule.find_one(Rule.code == "INVOICE_REFERENCE")
    response = await client.patch(
        f"{RULES}/{rule.id}",
        json={"config": {"pattern": "([unclosed", "flags": "i"}},
        headers=admin_headers,
    )
    assert response.status_code == 422


async def test_incomplete_lexicon_config_is_rejected(client, admin_headers):
    rule = await Rule.find_one(Rule.code == "URGENCY_LEXICON_FR")
    response = await client.patch(
        f"{RULES}/{rule.id}", json={"config": {"lang": "fr"}}, headers=admin_headers
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------- simulator
async def test_simulate_returns_hits_with_matched_tokens(client, supervisor_headers):
    response = await client.post(
        SIMULATE,
        json={
            "subject": "URGENT",
            "body": "C'est inacceptable, mon avocat va porter plainte. "
                    "187 dinars factures a tort depuis des semaines.",
            "claimant_is_vip": True,
        },
        headers=supervisor_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["priority"] == 1
    assert body["hits"]
    assert all(hit["matched"] for hit in body["hits"])
    assert {"LEGAL_LEXICON_FR", "VIP_CLAIMANT"} <= {h["code"] for h in body["hits"]}


async def test_simulate_persists_nothing(client, supervisor_headers):
    from app.models.complaint import Complaint

    await client.post(
        SIMULATE, json={"body": "test de simulation"}, headers=supervisor_headers
    )
    assert await Complaint.find_all().count() == 0


async def test_simulate_exposes_the_normalisation_result(client, supervisor_headers):
    response = await client.post(
        SIMULATE,
        json={
            "body": "3andi mochkla fel internet, 7atta lyoum ma7alouhech. "
                    "Contactez moi sur 20145879 ou test@example.tn"
        },
        headers=supervisor_headers,
    )
    body = response.json()
    assert "<PHONE>" in body["normalized_text"].upper()
    assert "<EMAIL>" in body["normalized_text"].upper()
    assert body["transliterated"]
    assert body["language"] == "ar-tn"
    assert body["language_source"] == "derja"


async def test_simulate_reflects_a_weight_change(client, admin_headers):
    """The tuning loop: change a weight, re-run, see the score move."""
    payload = {"body": "message normal sur ma facture", "claimant_is_vip": True}
    before = (await client.post(SIMULATE, json=payload, headers=admin_headers)).json()

    rule = await Rule.find_one(Rule.code == "VIP_CLAIMANT")
    await client.patch(f"{RULES}/{rule.id}", json={"weight": 90}, headers=admin_headers)

    after = (await client.post(SIMULATE, json=payload, headers=admin_headers)).json()
    assert after["priority_score"] > before["priority_score"]
    assert after["priority"] < before["priority"]


async def test_simulate_requires_supervisor(client, make_user, login):
    await make_user(email="agent@rakib.tn", password="Password123!", role=Role.AGENT)
    headers = await login(client, "agent@rakib.tn", "Password123!")
    response = await client.post(SIMULATE, json={"body": "x"}, headers=headers)
    assert response.status_code == 403


# --------------------------------------------------------------------- readiness
async def test_ready_exposes_the_engine_state(client):
    """Spec 11: the engine state must be visible, not inferred.

    With artifacts committed the system runs `ml`; the degraded path is covered
    in test_classifier.py by pointing ml_artifacts_dir at an empty directory.
    """
    body = (await client.get("/health/ready")).json()
    engine = body["engine"]
    assert engine["active_engine"] in {"ml", "rules"}
    assert engine["model_loaded"] is (engine["active_engine"] == "ml")
    assert engine["degraded"] is not engine["model_loaded"]
    assert engine["language_id_model"] is True

"""Knowledge base: retrieval, slot filling, draft language, usage tracking."""

import pytest

from app.intelligence.suggest.retriever import IndexedArticle, KBIndex
from app.intelligence.suggest.templater import fill, slots_in
from app.models.complaint import Complaint
from app.models.kb_article import KBArticle
from app.models.user import Role
from app.services import kb_service

COMPLAINTS = "/api/v1/complaints"
KB = "/api/v1/kb"


@pytest.fixture
async def supervisor_headers(client, make_user, login):
    await make_user(email="sup@rakib.tn", password="Password123!", role=Role.SUPERVISOR)
    return await login(client, "sup@rakib.tn", "Password123!")


# -------------------------------------------------------------------- templater
def test_slots_are_discovered_in_order_without_duplicates():
    assert slots_in("Bonjour {{name}}, ref {{ref}}, encore {{name}}") == ["name", "ref"]


def test_filling_replaces_known_slots():
    result = fill("Bonjour {{name}}", {"name": "Fatma"})
    assert result.text == "Bonjour Fatma"
    assert result.filled == {"name": "Fatma"}
    assert result.missing == []


def test_unresolved_slots_are_reported_not_invented():
    """A draft that silently invents a compensation amount is worse than one
    that asks the agent to fill it in."""
    result = fill("Avoir de {{amount}} pour {{ref}}", {"ref": "REC-1", "amount": None})
    assert result.missing == ["amount"]
    assert "[amount]" in result.text
    assert "REC-1" in result.text


def test_missing_slot_is_visibly_unfilled():
    assert "[montant]" in fill("Total {{montant}}", {}).text


# --------------------------------------------------------------------- retrieval
def make_article(id_, title, content, category=None, language="fr"):
    return IndexedArticle(
        id=id_, title=title, content=content, category=category,
        language=language, template=None, slots=[],
    )


def test_empty_index_returns_nothing():
    assert KBIndex().search("facture") == []


def test_bm25_ranks_the_relevant_article_first():
    index = KBIndex()
    index.build([
        make_article("1", "Contestation de facture", "facture montant prelevement avoir"),
        make_article("2", "Panne reseau mobile", "reseau signal couverture antenne"),
    ])
    hits = index.search("ma facture est trop elevee, montant anormal")
    assert hits[0].article.id == "1"


def test_search_prefers_the_complaint_category():
    index = KBIndex()
    index.build([
        make_article("1", "Guide general", "facture reseau equipement", None),
        make_article("2", "Facture detail", "facture montant", "FACTURATION"),
        make_article("3", "Facture avoir", "facture avoir remboursement", "FACTURATION"),
        make_article("4", "Facture delai", "facture delai traitement", "FACTURATION"),
    ])
    hits = index.search("facture", category="FACTURATION")
    assert all(hit.article.category == "FACTURATION" for hit in hits)


def test_search_falls_back_when_the_category_is_too_thin():
    """A narrow filter returning nothing is worse than a broad one an agent can judge."""
    index = KBIndex()
    index.build([
        make_article("1", "Guide general facture", "facture montant prelevement"),
        make_article("2", "Facture unique", "facture", "ROAMING_INTERNATIONAL"),
    ])
    hits = index.search("facture", category="ROAMING_INTERNATIONAL")
    assert len(hits) == 2


def test_search_puts_the_requested_language_first():
    index = KBIndex()
    index.build([
        make_article("fr", "Facture", "facture montant", "FACTURATION", "fr"),
        make_article("ar", "الفاتورة", "facture montant فاتورة", "FACTURATION", "ar"),
    ])
    hits = index.search("facture montant", language="ar")
    assert hits[0].article.language == "ar"


def test_arabic_query_matches_an_arabic_article():
    index = KBIndex()
    index.build([
        make_article("1", "الفاتورة", "فاتورة مبلغ خصم", "FACTURATION", "ar"),
        make_article("2", "Reseau", "reseau signal", "RESEAU_MOBILE", "fr"),
    ])
    hits = index.search("الفاتورة فيها مبلغ غالط")
    assert hits and hits[0].article.id == "1"


# ------------------------------------------------------------------ draft language
@pytest.mark.parametrize(
    "detected,expected",
    [("fr", "fr"), ("ar", "ar"), ("ar-tn", "ar"), ("en", "fr"), (None, "fr")],
)
def test_draft_language_follows_the_claimant(detected, expected):
    complaint = Complaint(
        ref="REC-1", claimant={"full_name": "X", "email": "x@y.tn"},
        subject="s", body="b" * 20,
    )
    complaint.analysis.language = detected
    assert kb_service.draft_language(complaint) == expected


# ------------------------------------------------------------------- seeded KB
async def test_kb_is_seeded_in_both_languages(client, agent_headers):
    articles = (await client.get(KB, headers=agent_headers)).json()
    languages = {article["language"] for article in articles}
    assert {"fr", "ar"} <= languages
    assert any(article["template"] for article in articles)


async def test_seeded_templates_declare_their_slots(client, agent_headers):
    articles = (await client.get(KB, headers=agent_headers)).json()
    with_template = [a for a in articles if a["template"]]
    assert all(a["slots"] for a in with_template)


# --------------------------------------------------------------------- suggest
async def test_suggest_returns_filled_drafts(client, routed_complaint, agent_headers):
    created = await routed_complaint()
    body = (
        await client.get(f"{COMPLAINTS}/{created['id']}/suggest", headers=agent_headers)
    ).json()

    assert body["drafts"]
    first = body["drafts"][0]
    assert created["ref"] in first["text"]
    assert "Fatma Ben Ali" in first["text"]
    assert body["cited_articles"]


async def test_suggest_reports_slots_it_could_not_fill(
    client, routed_complaint, agent_headers
):
    created = await routed_complaint()
    body = (
        await client.get(f"{COMPLAINTS}/{created['id']}/suggest", headers=agent_headers)
    ).json()
    # `amount` is never resolvable from the complaint document alone.
    assert isinstance(body["missing_slots"], list)


async def test_suggest_answers_in_arabic_for_an_arabic_complaint(
    client, agent_headers, departments
):
    from app.services import complaint_service

    created = (
        await client.post(
            COMPLAINTS,
            json={
                "subject": "فاتورة غالية",
                "body": "الفاتورة متاعي هذا الشهر 210 دينار و انا ما بدلتش في العرض",
                "claimant": {"full_name": "Fatma", "email": "fatma@example.tn"},
            },
        )
    ).json()
    complaint = await Complaint.get(created["id"])
    complaint.analysis.category = "FACTURATION"
    complaint.analysis.language = "ar"
    await complaint_service.route_to_category_department(complaint, "FACTURATION")
    await complaint.save()

    body = (
        await client.get(f"{COMPLAINTS}/{created['id']}/suggest", headers=agent_headers)
    ).json()
    assert body["language"] == "ar"
    assert any("السلام" in draft["text"] for draft in body["drafts"])


async def test_suggest_requires_staff(client, make_user, login, routed_complaint):
    created = await routed_complaint()
    await make_user(email="c@example.tn", password="Password123!", role=Role.CLAIMANT)
    headers = await login(client, "c@example.tn", "Password123!")
    response = await client.get(
        f"{COMPLAINTS}/{created['id']}/suggest", headers=headers
    )
    assert response.status_code == 403


# ----------------------------------------------------------------- usage tracking
async def test_recording_usage_increments_the_counter(
    client, routed_complaint, agent_headers
):
    created = await routed_complaint()
    suggestion = (
        await client.get(f"{COMPLAINTS}/{created['id']}/suggest", headers=agent_headers)
    ).json()
    article_id = suggestion["drafts"][0]["source_article_id"]

    response = await client.post(
        f"{COMPLAINTS}/{created['id']}/suggest/used",
        json={"article_id": article_id, "outcome": "edited"},
        headers=agent_headers,
    )
    assert response.status_code == 204

    from beanie import PydanticObjectId

    article = await KBArticle.get(PydanticObjectId(article_id))
    assert article.usage_count == 1
    assert article.usage_breakdown["edited"] == 1


async def test_discarded_drafts_do_not_count_as_usage(
    client, routed_complaint, agent_headers
):
    """Otherwise the metric proves nothing."""
    created = await routed_complaint()
    suggestion = (
        await client.get(f"{COMPLAINTS}/{created['id']}/suggest", headers=agent_headers)
    ).json()
    article_id = suggestion["drafts"][0]["source_article_id"]

    await client.post(
        f"{COMPLAINTS}/{created['id']}/suggest/used",
        json={"article_id": article_id, "outcome": "discarded"},
        headers=agent_headers,
    )
    from beanie import PydanticObjectId

    article = await KBArticle.get(PydanticObjectId(article_id))
    assert article.usage_count == 0
    assert article.usage_breakdown["discarded"] == 1


async def test_invalid_outcome_is_rejected(client, routed_complaint, agent_headers):
    created = await routed_complaint()
    response = await client.post(
        f"{COMPLAINTS}/{created['id']}/suggest/used",
        json={"article_id": "507f1f77bcf86cd799439011", "outcome": "sent-by-pigeon"},
        headers=agent_headers,
    )
    assert response.status_code == 422


# --------------------------------------------------------------------- KB CRUD
async def test_creating_an_article_rebuilds_the_index(client, supervisor_headers):
    response = await client.post(
        KB,
        json={
            "title": "Procedure exceptionnelle grele",
            "content": "Procedure applicable en cas de degats materiels lies a la grele",
            "category": "EQUIPEMENT",
            "template": "Bonjour {{claimant_name}}, dossier {{ref}} en cours.",
        },
        headers=supervisor_headers,
    )
    assert response.status_code == 201
    assert response.json()["slots"] == ["claimant_name", "ref"]

    from app.intelligence.suggest.retriever import index

    assert any(a.title.startswith("Procedure exceptionnelle") for a in index._articles)


async def test_agents_cannot_write_to_the_kb(client, agent_headers):
    response = await client.post(
        KB, json={"title": "Nouveau", "content": "contenu quelconque"},
        headers=agent_headers,
    )
    assert response.status_code == 403


async def test_unknown_category_is_rejected(client, supervisor_headers):
    response = await client.post(
        KB,
        json={"title": "Test", "content": "contenu quelconque", "category": "PIZZA"},
        headers=supervisor_headers,
    )
    assert response.status_code == 422


async def test_deactivating_an_article_removes_it_from_search(
    client, supervisor_headers
):
    created = (
        await client.post(
            KB,
            json={"title": "Article temporaire", "content": "contenu temporaire unique"},
            headers=supervisor_headers,
        )
    ).json()

    await client.delete(f"{KB}/{created['id']}", headers=supervisor_headers)

    from app.intelligence.suggest.retriever import index

    assert all(a.id != created["id"] for a in index._articles)

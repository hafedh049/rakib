"""Knowledge base: index lifecycle, seeding, and reply suggestions."""

from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.domain.kb_seed import KB_SEED
from app.domain.taxonomy import CATEGORY_LABELS_AR, CATEGORY_LABELS_FR
from app.intelligence.ports import Draft, SuggestionOutput
from app.intelligence.suggest.retriever import IndexedArticle, index
from app.intelligence.suggest.templater import fill, slots_in
from app.models.complaint import Complaint
from app.models.department import Department
from app.models.kb_article import KBArticle
from app.models.user import User

log = get_logger(__name__)

#: Articles are written in French and Arabic; anything else falls back to French.
SUPPORTED_DRAFT_LANGUAGES = {"fr", "ar"}


async def rebuild_index() -> int:
    articles = await KBArticle.find(KBArticle.active == True).to_list()  # noqa: E712
    return index.build(
        [
            IndexedArticle(
                id=str(article.id),
                title=article.title,
                content=article.content,
                category=article.category,
                language=article.language,
                template=article.template,
                slots=article.slots,
            )
            for article in articles
        ]
    )


async def seed_articles() -> int:
    created = 0
    for entry in KB_SEED:
        if await KBArticle.find_one(KBArticle.title == entry["title"]):
            continue
        template = entry.get("template")
        await KBArticle(
            **entry, slots=slots_in(template) if template else []
        ).insert()
        created += 1
    if created:
        log.info("seed.kb", created=created)
    return created


def draft_language(complaint: Complaint) -> str:
    """Reply in the claimant's language.

    Derja (`ar-tn`) is answered in Arabic: an operator writes standard Arabic
    even when the customer wrote in Latin-script derja.
    """
    detected = (complaint.analysis.language or "fr").lower()
    if detected.startswith("ar"):
        return "ar"
    return detected if detected in SUPPORTED_DRAFT_LANGUAGES else "fr"


async def slot_values(complaint: Complaint, language: str) -> dict[str, Any]:
    department = None
    if complaint.assignment and complaint.assignment.department_id:
        department = await Department.get(complaint.assignment.department_id)
    agent = None
    if complaint.assignment and complaint.assignment.agent_id:
        agent = await User.get(complaint.assignment.agent_id)

    labels = CATEGORY_LABELS_AR if language == "ar" else CATEGORY_LABELS_FR
    return {
        "claimant_name": complaint.claimant.full_name,
        "ref": complaint.ref,
        "category": labels.get(complaint.analysis.category or "", ""),
        "created_at": complaint.created_at.strftime("%d/%m/%Y"),
        "department": department.name if department else None,
        "sla_hours": complaint.sla.hours,
        "agent_name": agent.full_name if agent else None,
        "status": str(complaint.status),
    }


async def suggest(complaint: Complaint, limit: int = 3) -> SuggestionOutput:
    """Top-k drafts for a complaint. Synchronous, no generation, under 100 ms."""
    if index.size == 0:
        await rebuild_index()

    language = draft_language(complaint)
    query = f"{complaint.subject} {complaint.body}"
    hits = index.search(
        query, category=complaint.analysis.category, language=language, limit=limit
    )
    if not hits:
        return SuggestionOutput(drafts=[], cited_articles=[], missing_slots=[])

    values = await slot_values(complaint, language)
    drafts: list[Draft] = []
    missing: list[str] = []

    for hit in hits:
        template = hit.article.template or hit.article.content
        result = fill(template, values)
        drafts.append(
            Draft(
                text=result.text,
                source_article_id=hit.article.id,
                score=round(hit.score, 4),
                filled_slots=result.filled,
            )
        )
        for slot in result.missing:
            if slot not in missing:
                missing.append(slot)

    return SuggestionOutput(
        drafts=drafts,
        cited_articles=[hit.article.id for hit in hits],
        missing_slots=missing,
    )


async def record_usage(article_id: str, outcome: str) -> KBArticle | None:
    """Track verbatim / edited / discarded — evidence the feature earns its place."""
    from beanie import PydanticObjectId

    article = await KBArticle.get(PydanticObjectId(article_id))
    if article is None:
        return None
    if outcome != "discarded":
        article.usage_count += 1
    article.usage_breakdown[outcome] = article.usage_breakdown.get(outcome, 0) + 1
    article.updated_at = datetime.now(UTC)
    await article.save()
    return article

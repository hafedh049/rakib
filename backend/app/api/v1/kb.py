from datetime import UTC, datetime
from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import NotFound, ValidationError
from app.deps import AgentUser, SupervisorUser
from app.domain.taxonomy import ALL_CATEGORIES
from app.intelligence.suggest.templater import slots_in
from app.models.kb_article import KBArticle
from app.services import kb_service

router = APIRouter(prefix="/kb", tags=["kb"])


class ArticleIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=10, max_length=20_000)
    category: str | None = None
    language: str = "fr"
    tags: list[str] = Field(default_factory=list)
    template: str | None = None
    active: bool = True


class ArticlePatch(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    template: str | None = None
    active: bool | None = None


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    title: str
    content: str
    category: str | None
    language: str
    tags: list[str]
    template: str | None
    slots: list[str]
    usage_count: int
    usage_breakdown: dict[str, int]
    active: bool
    updated_at: datetime


def _validate(category: str | None, language: str | None) -> None:
    if category and category not in ALL_CATEGORIES:
        raise ValidationError(f"Categorie inconnue: {category}")
    if language and language not in {"fr", "ar"}:
        raise ValidationError("Langue non supportee (fr | ar)")


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    _: AgentUser,
    category: Annotated[str | None, Query()] = None,
    language: Annotated[str | None, Query()] = None,
) -> list[KBArticle]:
    query: dict = {}
    if category:
        query["category"] = category
    if language:
        query["language"] = language
    return await KBArticle.find(query).sort("-usage_count").to_list()


@router.post("", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
async def create_article(payload: ArticleIn, _: SupervisorUser) -> KBArticle:
    _validate(payload.category, payload.language)
    article = KBArticle(
        **payload.model_dump(),
        slots=slots_in(payload.template) if payload.template else [],
    )
    await article.insert()
    await kb_service.rebuild_index()
    return article


@router.patch("/{article_id}", response_model=ArticleOut)
async def patch_article(
    article_id: PydanticObjectId, payload: ArticlePatch, _: SupervisorUser
) -> KBArticle:
    article = await KBArticle.get(article_id)
    if article is None:
        raise NotFound("Article introuvable")

    updates = payload.model_dump(exclude_unset=True)
    _validate(updates.get("category"), updates.get("language"))
    for field, value in updates.items():
        setattr(article, field, value)
    if "template" in updates:
        article.slots = slots_in(article.template) if article.template else []
    article.updated_at = datetime.now(UTC)
    await article.save()
    await kb_service.rebuild_index()
    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_article(
    article_id: PydanticObjectId, _: SupervisorUser
) -> None:
    """Soft delete — usage statistics are evidence and should survive."""
    article = await KBArticle.get(article_id)
    if article is None:
        raise NotFound("Article introuvable")
    article.active = False
    article.updated_at = datetime.now(UTC)
    await article.save()
    await kb_service.rebuild_index()


@router.post("/reindex")
async def reindex(_: SupervisorUser) -> dict[str, int]:
    return {"indexed": await kb_service.rebuild_index()}

from datetime import UTC, datetime

import pymongo
from beanie import Document
from pydantic import Field


class KBArticle(Document):
    """A knowledge-base entry, optionally carrying a reply template.

    `language` is load-bearing rather than metadata: the draft handed to an
    agent is written in the language the claimant used, which is the visible
    consequence of the language-identification stage.
    """

    title: str
    content: str
    category: str | None = None
    language: str = "fr"          # fr | ar
    tags: list[str] = Field(default_factory=list)
    #: Reply template with {{slots}}; None means the article is reference only.
    template: str | None = None
    slots: list[str] = Field(default_factory=list)
    usage_count: int = 0
    #: verbatim / edited / discarded — proves the feature is actually used.
    usage_breakdown: dict[str, int] = Field(default_factory=dict)
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "kb_articles"
        indexes = [
            pymongo.IndexModel([("category", 1), ("language", 1)], name="kb_category"),
            pymongo.IndexModel([("active", 1)], name="kb_active"),
            pymongo.IndexModel([("usage_count", -1)], name="kb_usage"),
        ]

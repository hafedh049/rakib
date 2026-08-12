from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import pymongo
from beanie import Document
from pydantic import Field


class RuleKind(StrEnum):
    LEXICON = "lexicon"
    REGEX = "regex"
    FIELD = "field"
    HISTORY = "history"
    LENGTH = "length"
    CATEGORY_WEIGHT = "category_weight"


class Rule(Document):
    """A scoring rule, editable from the admin UI.

    Rules live in Mongo rather than in code on purpose: a supervisor tuning a
    weight and watching the effect in the simulator is a feature of the product,
    not a configuration chore (spec 5.4).
    """

    code: str
    label: str
    kind: RuleKind
    config: dict[str, Any] = Field(default_factory=dict)
    weight: int = 0
    active: bool = True
    order: int = 100
    #: Set on seeded rules so a reseed can refresh them without clobbering
    #: anything an admin created by hand.
    builtin: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "rules"
        indexes = [
            pymongo.IndexModel([("code", 1)], unique=True, name="rule_code"),
            pymongo.IndexModel([("active", 1), ("order", 1)], name="rule_active_order"),
        ]

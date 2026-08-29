from datetime import UTC, datetime

import pymongo
from beanie import Document
from pydantic import Field


class Department(Document):
    code: str
    name: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    #: Deactivated departments keep their history but take no new complaints.
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "departments"
        indexes = [
            pymongo.IndexModel([("code", 1)], unique=True, name="department_code"),
            pymongo.IndexModel([("active", 1)], name="department_active"),
        ]

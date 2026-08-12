from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import EmailStr, Field


class Role(StrEnum):
    CLAIMANT = "claimant"
    AGENT = "agent"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


#: Ordered from least to most privileged. Used by the RBAC dependency so a
#: `require_role(AGENT)` route also admits supervisors and admins.
ROLE_ORDER: dict[Role, int] = {
    Role.CLAIMANT: 0,
    Role.AGENT: 1,
    Role.SUPERVISOR: 2,
    Role.ADMIN: 3,
}


def role_at_least(role: Role | str, minimum: Role) -> bool:
    try:
        return ROLE_ORDER[Role(role)] >= ROLE_ORDER[minimum]
    except ValueError:
        return False


class User(Document):
    email: EmailStr
    password_hash: str
    full_name: str
    role: Role = Role.CLAIMANT
    department_id: PydanticObjectId | None = None
    skills: list[str] = Field(default_factory=list)
    max_concurrent: int = 20
    is_active: bool = True
    locale: str = "fr"
    phone: str | None = None
    last_active_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "users"
        indexes = [
            pymongo.IndexModel([("email", 1)], unique=True, name="user_email_unique"),
            pymongo.IndexModel(
                [("department_id", 1), ("role", 1), ("is_active", 1)],
                name="user_dept_role",
            ),
        ]

    @property
    def is_staff(self) -> bool:
        return role_at_least(self.role, Role.AGENT)

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

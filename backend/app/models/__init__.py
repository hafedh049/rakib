"""Beanie document registry.

Every Document class must be listed in ALL_DOCUMENTS or Beanie will not build its
indexes. Later phases append to this list as their models land.
"""

from beanie import Document

from app.models.refresh_token import RefreshToken
from app.models.user import Role, User, role_at_least

ALL_DOCUMENTS: list[type[Document]] = [
    User,
    RefreshToken,
]

__all__ = ["ALL_DOCUMENTS", "RefreshToken", "Role", "User", "role_at_least"]

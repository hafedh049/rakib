from datetime import UTC, datetime

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import Field


class RefreshToken(Document):
    """Only the SHA-256 of the token is stored; the raw value never touches the DB."""

    user_id: PydanticObjectId
    token_hash: str
    expires_at: datetime
    revoked: bool = False
    replaced_by: str | None = None
    user_agent: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "refresh_tokens"
        indexes = [
            pymongo.IndexModel(
                [("token_hash", 1)], unique=True, name="refresh_hash_unique"
            ),
            pymongo.IndexModel([("user_id", 1), ("revoked", 1)], name="refresh_user"),
            # TTL: Mongo reaps expired rows so the collection cannot grow unbounded.
            pymongo.IndexModel(
                [("expires_at", 1)], expireAfterSeconds=0, name="refresh_ttl"
            ),
        ]

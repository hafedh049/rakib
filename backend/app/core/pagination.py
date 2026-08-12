"""Opaque cursor pagination.

Keyset pagination on ``(created_at DESC, _id DESC)`` — stable under concurrent
inserts, unlike skip/limit which shifts rows under the reader. The cursor is
base64 so callers treat it as opaque and we can change the encoding later.
"""

import base64
import binascii
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from beanie import PydanticObjectId
from pydantic import BaseModel

from app.core.errors import ValidationError

T = TypeVar("T")

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


def encode_cursor(created_at: datetime, object_id: PydanticObjectId) -> str:
    raw = f"{created_at.astimezone(UTC).isoformat()}|{object_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, PydanticObjectId]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        timestamp, object_id = raw.split("|", 1)
        return datetime.fromisoformat(timestamp), PydanticObjectId(object_id)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValidationError("Curseur de pagination invalide") from exc


def cursor_filter(cursor: str | None) -> dict[str, Any]:
    """Mongo filter selecting everything strictly after the cursor position."""
    if not cursor:
        return {}
    created_at, object_id = decode_cursor(cursor)
    return {
        "$or": [
            {"created_at": {"$lt": created_at}},
            {"created_at": created_at, "_id": {"$lt": object_id}},
        ]
    }


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_PAGE_SIZE
    return max(1, min(limit, MAX_PAGE_SIZE))

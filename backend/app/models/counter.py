"""Atomic per-year reference counter.

`findAndModify` with `$inc` and `upsert` is atomic in MongoDB, so two concurrent
submissions can never receive the same ref — no application-level locking.

The ref is a DISPLAY identifier only (the number a claimant reads out on the
phone). It grants no access: reading a complaint requires a signed tracking
token or an authenticated session. See core/security.create_tracking_token.
"""

from datetime import UTC, datetime

import pymongo
from beanie import Document

REF_PREFIX = "REC"


class Counter(Document):
    """One document per counter key, e.g. `complaint_ref:2026`."""

    key: str
    value: int = 0

    class Settings:
        name = "counters"
        indexes = [pymongo.IndexModel([("key", 1)], unique=True, name="counter_key")]


async def next_complaint_ref(now: datetime | None = None) -> str:
    """Return the next reference, e.g. ``REC-2026-00412``."""
    moment = now or datetime.now(UTC)
    year = moment.year
    key = f"complaint_ref:{year}"

    document = await Counter.get_motor_collection().find_one_and_update(
        {"key": key},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=pymongo.ReturnDocument.AFTER,
    )
    return f"{REF_PREFIX}-{year}-{document['value']:05d}"

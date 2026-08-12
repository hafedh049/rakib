"""Redis Stream event bus.

`publish()` never raises into the caller. A complaint being created is more
important than a notification being delivered, so a Redis outage degrades
notifications rather than failing the request (spec 4.3).
"""

from typing import Any, cast

import redis.asyncio as aioredis

from app.config import settings
from app.core.logging import get_logger
from app.events.types import STREAM_KEY, Event, EventName

log = get_logger(__name__)

#: Streams are capped so a long-running deployment cannot grow unbounded.
MAX_STREAM_LENGTH = 50_000

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.redis_url, decode_responses=True, socket_timeout=5
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def publish(event: EventName, payload: dict[str, Any]) -> str | None:
    """Append an event to the stream. Returns the stream id, or None on failure."""
    envelope = Event(name=event, payload=payload)
    try:
        stream_id = await get_redis().xadd(
            STREAM_KEY,
            # cast: redis-py types the field mapping with a wide key union that
            # dict[str, str] cannot satisfy under invariance.
            cast("Any", envelope.to_stream()),
            maxlen=MAX_STREAM_LENGTH,
            approximate=True,
        )
    except Exception as exc:  # noqa: BLE001 — never propagate into the request
        log.error("events.publish_failed", event_name=str(event), error=str(exc))
        return None
    log.info("events.published", event_name=str(event), stream_id=stream_id)
    return str(stream_id)


async def ensure_group(group: str) -> None:
    """Create the consumer group, tolerating the case where it already exists."""
    try:
        await get_redis().xgroup_create(
            STREAM_KEY, group, id="$", mkstream=True
        )
        log.info("events.group_created", group=group)
    except Exception as exc:  # noqa: BLE001 — BUSYGROUP is the expected path
        if "BUSYGROUP" not in str(exc):
            log.warning("events.group_create_failed", group=group, error=str(exc))


async def health() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:  # noqa: BLE001 — a health probe must never raise
        return False

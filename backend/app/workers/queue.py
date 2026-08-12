"""Job enqueueing from the API process.

Enqueue failures are logged, never raised: `POST /complaints` must return in
under 100 ms and must not fail because the queue is briefly unreachable. A
complaint whose job was lost is still visible with `triage_state = pending`, and
a supervisor can re-triage it.
"""

from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_pool: ArqRedis | None = None


async def get_pool() -> ArqRedis | None:
    global _pool
    if _pool is None:
        try:
            _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        except Exception as exc:  # noqa: BLE001 — queue is not on the request path
            log.error("queue.connect_failed", error=str(exc))
            return None
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def enqueue(function: str, *args: Any, **kwargs: Any) -> str | None:
    pool = await get_pool()
    if pool is None:
        return None
    try:
        job = await pool.enqueue_job(function, *args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        log.error("queue.enqueue_failed", function=function, error=str(exc))
        return None
    return job.job_id if job else None

"""API-side consumer that feeds the SSE broker.

The notify worker owns email and the other out-of-band channels. Browser
connections live in the API process, so the API reads the same stream under its
own consumer group and fans out in memory.
"""

import asyncio

from app.core.logging import get_logger
from app.events import bus
from app.events.dispatch import dispatch
from app.events.types import STREAM_KEY, Event

log = get_logger(__name__)

GROUP = "sse"
CONSUMER = "api-1"
BLOCK_MS = 5_000

_task: asyncio.Task | None = None


async def _loop() -> None:
    redis = bus.get_redis()
    await bus.ensure_group(GROUP)
    log.info("sse_consumer.started", group=GROUP)

    while True:
        try:
            batches = await redis.xreadgroup(
                GROUP, CONSUMER, {STREAM_KEY: ">"}, count=50, block=BLOCK_MS
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — keep the API alive regardless
            log.warning("sse_consumer.read_failed", error=str(exc))
            await asyncio.sleep(3)
            continue

        for _stream, messages in batches or []:
            for message_id, fields in messages:
                try:
                    event = Event.from_stream(fields)
                    await dispatch(event.name, event.payload, runs_in="api")
                except Exception as exc:  # noqa: BLE001
                    log.warning("sse_consumer.dispatch_failed", error=str(exc))
                finally:
                    await redis.xack(STREAM_KEY, GROUP, message_id)


async def start() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop(), name="sse-consumer")


async def stop() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
        _task = None

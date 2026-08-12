"""Consumes the `events` stream and fans out to the out-of-band notifiers.

Runs as its own process (see docker-compose). Uses a Redis consumer group so
messages survive a restart and are acknowledged only once delivered.
"""

import asyncio
import signal
from typing import Any

from app.core.logging import configure_logging, get_logger
from app.events import bus
from app.events.dispatch import dispatch
from app.events.types import STREAM_KEY, Event

log = get_logger(__name__)

GROUP = "notifiers"
CONSUMER = "notify-1"
BLOCK_MS = 5_000
BATCH = 20

_stop = asyncio.Event()


async def handle(fields: dict[str, Any]) -> None:
    event = Event.from_stream(fields)
    delivered = await dispatch(event.name, event.payload, runs_in="worker")
    log.info(
        "notify.handled", event_name=str(event.name), delivered=delivered,
        ref=event.payload.get("ref"),
    )


async def consume() -> None:
    redis = bus.get_redis()
    await bus.ensure_group(GROUP)
    log.info("notify.started", group=GROUP, consumer=CONSUMER)

    while not _stop.is_set():
        try:
            batches = await redis.xreadgroup(
                GROUP, CONSUMER, {STREAM_KEY: ">"}, count=BATCH, block=BLOCK_MS
            )
        except Exception as exc:  # noqa: BLE001 — reconnect rather than die
            log.error("notify.read_failed", error=str(exc))
            await asyncio.sleep(2)
            continue

        for _stream, messages in batches or []:
            for message_id, fields in messages:
                try:
                    await handle(fields)
                except Exception as exc:  # noqa: BLE001
                    log.error(
                        "notify.handler_failed", id=message_id, error=str(exc)
                    )
                finally:
                    # Acknowledged either way: a poison message must not block
                    # the stream. The failure is in the logs.
                    await redis.xack(STREAM_KEY, GROUP, message_id)


async def main() -> None:
    configure_logging()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop.set)
        except NotImplementedError:  # pragma: no cover — Windows
            pass
    try:
        await consume()
    finally:
        await bus.close_redis()
        log.info("notify.stopped")


if __name__ == "__main__":
    asyncio.run(main())

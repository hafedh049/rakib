"""Fire-and-forget side effects.

Publishing an event and enqueueing the triage job are both already best-effort:
neither may fail a complaint submission, and the caller ignores their result.
Awaiting them inline therefore buys nothing and costs two Redis round trips on
the one request a human is actually waiting for.

Tasks are kept in a set because asyncio only holds a weak reference to them —
without this they can be garbage-collected mid-flight.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any

from app.core.logging import get_logger

log = get_logger(__name__)

_pending: set[asyncio.Task[Any]] = set()


def spawn(coro: Coroutine[Any, Any, Any], *, name: str) -> None:
    try:
        task = asyncio.create_task(coro, name=name)
    except RuntimeError:
        # No running loop (scripts, tests calling services directly): just skip
        # the side effect rather than exploding.
        coro.close()
        log.warning("background.no_loop", task=name)
        return

    _pending.add(task)
    task.add_done_callback(_finished)


def _finished(task: asyncio.Task[Any]) -> None:
    _pending.discard(task)
    if task.cancelled():
        return
    error = task.exception()
    if error is not None:
        log.error("background.failed", task=task.get_name(), error=str(error))


async def drain(seconds: float = 5.0) -> None:
    """Let in-flight side effects finish on shutdown."""
    if not _pending:
        return
    await asyncio.wait(set(_pending), timeout=seconds)

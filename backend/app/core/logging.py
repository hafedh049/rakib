"""Structured JSON logging with request_id / complaint_ref bound in context."""

import logging
import sys
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response

from app.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=settings.log_level.upper()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id, method=request.method, path=request.url.path
    )
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


def bind_complaint(ref: str) -> None:
    """Bind a complaint ref into the logging context for the rest of the request/job."""
    structlog.contextvars.bind_contextvars(complaint_ref=ref)

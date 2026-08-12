from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app import db
from app.api.v1 import api_router
from app.api.v1 import health as health_routes
from app.config import settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import configure_logging, get_logger, request_context_middleware
from app.events import bus
from app.services import (
    kb_service,
    rules_service,
    seed_service,
    sse_consumer,
    storage,
    triage,
)
from app.workers import queue

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await db.init_db()
    await seed_service.seed_departments()
    await rules_service.seed_rules()
    await kb_service.seed_articles()
    await kb_service.rebuild_index()
    await triage.refresh_rules()
    try:
        await storage.ensure_bucket()
    except Exception as exc:  # noqa: BLE001 — object storage must not block startup
        log.warning("storage.unavailable_at_boot", error=str(exc))
    await sse_consumer.start()
    log.info("app.started", env=settings.environment, backend=settings.triage_backend)
    yield
    await sse_consumer.stop()
    await queue.close_pool()
    await bus.close_redis()
    await db.close_db()
    log.info("app.stopped")


app = FastAPI(
    title="Rakib — Gestion intelligente des reclamations",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.middleware("http")(request_context_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, settings.public_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)

app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(RequestValidationError)
async def _validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic failures come back as problem+json like every other error."""
    return JSONResponse(
        status_code=422,
        media_type="application/problem+json",
        content={
            "type": "/errors/validation",
            "title": "Donnees invalides",
            "status": 422,
            "detail": "La requete contient des champs invalides",
            "instance": str(request.url.path),
            "errors": [
                {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
                for e in exc.errors()
            ],
        },
    )


app.include_router(health_routes.router)
app.include_router(api_router, prefix=settings.api_prefix)

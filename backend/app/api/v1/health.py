from typing import Any

from fastapi import APIRouter, Response, status

from app import db
from app.config import settings
from app.events import bus
from app.notifiers.sse import broker
from app.services import triage

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Liveness. Deliberately dependency-free so it never flaps on a Mongo hiccup."""
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


@router.get("/health/ready")
async def ready(response: Response) -> dict[str, Any]:
    """Readiness, including the degraded-mode indicator required by spec 11.

    The engine loads no artifact, so readiness is about Mongo and Redis —
    and that state has to be visible here rather than inferred.
    """
    engine = triage.health()

    # Redis backs notifications, not the request path — it is reported but does
    # not make the service unready.
    checks = {"mongo": await db.ping()}
    optional = {"redis": await bus.health()}
    ready_now = all(checks.values())
    if not ready_now:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready_now else "not-ready",
        "checks": {**checks, **optional},
        "sse_clients": broker.subscriber_count,
        "engine": {
            "configured_backend": settings.triage_backend,
            "active_engine": engine.name,
            "engine_ready": engine.engine_ready,
            "engine_version": engine.engine_version,
            "degraded": engine.degraded,
            "detail": engine.detail,
        },
    }

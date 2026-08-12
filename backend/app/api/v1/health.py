from typing import Any

from fastapi import APIRouter, Response, status

from app import db
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Liveness. Deliberately dependency-free so it never flaps on a Mongo hiccup."""
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


@router.get("/health/ready")
async def ready(response: Response) -> dict[str, Any]:
    """Readiness. Reports degraded mode explicitly — §11 requires the engine state
    to be visible here when ml_artifacts/ is empty."""
    mongo_ok = await db.ping()

    # Populated from Phase 5 onward; until then the system is honestly rules-only.
    engine: dict[str, Any] = {
        "configured_backend": settings.triage_backend,
        "active_engine": "rules",
        "model_loaded": False,
        "model_version": None,
        "degraded": True,
        "degraded_reason": "classifier not yet built (phase 5)",
    }

    checks = {"mongo": mongo_ok}
    ready_now = all(checks.values())
    if not ready_now:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready_now else "not-ready", "checks": checks, "engine": engine}

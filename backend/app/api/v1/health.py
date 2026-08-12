from typing import Any

from fastapi import APIRouter, Response, status

from app import db
from app.config import settings
from app.intelligence.text import language as lid
from app.services import triage

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Liveness. Deliberately dependency-free so it never flaps on a Mongo hiccup."""
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


@router.get("/health/ready")
async def ready(response: Response) -> dict[str, Any]:
    """Readiness, including the degraded-mode indicator required by spec 11.

    Deleting `ml_artifacts/` and restarting must still yield a working system —
    and that state has to be visible here rather than inferred.
    """
    mongo_ok = await db.ping()
    engine = triage.health()

    checks = {"mongo": mongo_ok}
    ready_now = all(checks.values())
    if not ready_now:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready_now else "not-ready",
        "checks": checks,
        "engine": {
            "configured_backend": settings.triage_backend,
            "active_engine": engine.name,
            "model_loaded": engine.model_loaded,
            "model_version": engine.model_version,
            "degraded": engine.degraded,
            "detail": engine.detail,
            "language_id_model": lid.model_available(),
        },
    }

"""Retraining job and its daily trigger check.

Retraining is CPU-bound and takes tens of seconds on the 2-vCPU envelope this
project targets, so it never runs in a request. The daily cron only *checks*
whether enough corrections have accumulated; it does not train on a schedule,
because training on unchanged data would churn versions for nothing.
"""

from typing import Any

from app.core.logging import get_logger
from app.intelligence.training.trainer import NotEnoughData
from app.services import learning_service

log = get_logger(__name__)


async def retrain_model(ctx: dict[str, Any], triggered_by: str = "manual") -> dict:
    try:
        record = await learning_service.retrain(triggered_by=triggered_by)
    except NotEnoughData as exc:
        log.warning("retrain.refused", reason=str(exc))
        return {"status": "refused", "reason": str(exc)}

    return {
        "status": "promoted" if record.promoted else "rejected",
        "version": record.version,
        "macro_f1": record.macro_f1,
        "rejection_reason": record.rejection_reason,
    }


async def check_retrain_trigger(ctx: dict[str, Any]) -> dict:
    """Daily: retrain only once enough corrections have piled up (spec 5.8)."""
    should, pending = await learning_service.should_retrain()
    if not should:
        return {"status": "skipped", "pending_corrections": pending}

    log.info("retrain.triggered", pending_corrections=pending)
    return await retrain_model(ctx, triggered_by=f"auto:{pending}_corrections")

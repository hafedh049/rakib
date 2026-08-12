"""Background triage job.

`POST /complaints` returns immediately; this runs the pipeline a moment later.
The job is idempotent: re-running it re-analyses the complaint and overwrites
the analysis, which is exactly what /retriage needs.
"""

from typing import Any

from beanie import PydanticObjectId

from app.core.logging import bind_complaint, get_logger
from app.models.complaint import Complaint
from app.services import triage_service

log = get_logger(__name__)


async def triage_complaint(ctx: dict[str, Any], complaint_id: str) -> dict[str, Any]:
    complaint = await Complaint.get(PydanticObjectId(complaint_id))
    if complaint is None:
        log.warning("triage_job.missing_complaint", complaint_id=complaint_id)
        return {"status": "missing"}

    bind_complaint(complaint.ref)
    await triage_service.triage_complaint(complaint)
    return {
        "status": str(complaint.triage_state),
        "category": complaint.analysis.category,
        "priority": complaint.analysis.priority,
    }

"""Running a complaint through the engine and recording what it decided.

The decision *rules* live here rather than in the engine: the engine says what
a complaint is about, this module says what the application then does with that
— which department owns it, whether an agent must look at it, what the timeline
records. Keeping the two apart is what let the categoriser be replaced without
touching any of this.
"""

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.events.bus import publish
from app.events.types import EventName
from app.models.complaint import (
    CLOSED_STATUSES,
    Analysis,
    Assignment,
    AssignmentMethod,
    Complaint,
    Status,
    TimelineEntry,
    TriageState,
)
from app.models.department import Department
from app.intelligence.ports import DepartmentInfo, TriageInput
from app.services import complaint_service, triage

log = get_logger(__name__)


async def build_input(complaint: Complaint) -> TriageInput:
    departments = await Department.find(Department.active == True).to_list()  # noqa: E712
    return TriageInput(
        subject=complaint.subject,
        body=complaint.body,
        channel=str(complaint.channel),
        claimant_email=complaint.claimant.email,
        departments=[
            DepartmentInfo(
                code=d.code,
                name=d.name,
                keywords=list(d.keywords),
                categories=list(d.categories),
            )
            for d in departments
        ],
    )


async def triage_complaint(complaint: Complaint) -> Complaint:
    """Analyse, route, and record. Never raises into the caller."""
    engine = triage.get_engine()

    try:
        output = await engine.analyze(await build_input(complaint))
    except Exception as exc:  # noqa: BLE001 — a failed analysis must not lose the complaint
        log.error("triage.failed", ref=complaint.ref, error=str(exc))
        await complaint_service.persist_fields(
            complaint, {"triage_state": str(TriageState.FAILED)}
        )
        return complaint

    complaint.analysis = Analysis(
        category=output.category,
        category_confidence=output.category_confidence,
        category_alternatives=output.category_alternatives,
        language=output.language,
        keywords=output.keywords,
        evidence=output.evidence,
        needs_human_triage=output.needs_human_triage,
        triage_reason=output.triage_reason,
        engine=output.engine,
        engine_version=output.engine_version,
        latency_ms=output.latency_ms,
        analyzed_at=datetime.now(UTC),
    )
    complaint.normalized_text = output.normalized_text
    complaint.triage_state = TriageState.DONE

    department = await Department.find_one(Department.code == output.department_code)
    complaint.assignment = complaint.assignment or Assignment()
    complaint.assignment.department_id = department.id if department else None
    complaint.assignment.department_code = department.code if department else None
    # The complaint lands in the department queue. An admin assigns the agent —
    # that hand-off is a human decision by design.
    complaint.assignment.method = AssignmentMethod.QUEUE

    entries = [
        TimelineEntry(
            action="triage.done",
            actor_type="engine",
            meta={
                "category": output.category,
                "department": output.department_code,
                "needs_human": output.needs_human_triage,
            },
        )
    ]

    fields: dict = {
        "analysis": complaint.analysis.model_dump(),
        "normalized_text": complaint.normalized_text,
        "triage_state": str(complaint.triage_state),
        "assignment": complaint.assignment.model_dump(),
    }
    # Only advance a complaint that is still at the start of its life: a
    # re-analysis must never drag a resolved or closed one back to "triaged".
    if complaint.status is Status.NEW:
        complaint.status = Status.TRIAGED
        fields["status"] = str(Status.TRIAGED)

    await complaint_service.persist_fields(complaint, fields, entries)

    await publish(
        EventName.COMPLAINT_TRIAGED,
        complaint_service.event_payload(complaint, category=output.category),
    )
    log.info(
        "triage.done",
        ref=complaint.ref,
        category=output.category,
        department=output.department_code,
        latency_ms=output.latency_ms,
    )
    return complaint


async def retriage(complaint: Complaint) -> Complaint:
    """Re-run the analysis. Refused on a closed complaint."""
    if complaint.status in CLOSED_STATUSES:
        return complaint
    return await triage_complaint(complaint)

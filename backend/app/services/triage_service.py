"""Orchestration around the pipeline: gather context, decide, persist, notify.

The decision rules of spec 5.6 live here rather than in the engine. The engine
is a function of text; whether a given confidence is good enough, and what to do
when it is not, is policy that a supervisor may want to change.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from beanie import PydanticObjectId

from app.config import settings
from app.core.logging import get_logger
from app.domain.taxonomy import ALL_CATEGORIES, GENERAL_DEPARTMENT_CODE
from app.events.bus import publish
from app.events.types import EventName
from app.intelligence import pipeline
from app.intelligence.ports import DedupCandidate, DepartmentInfo, TriageInput
from app.models.analysis_trace import AnalysisTrace, TraceStage
from app.models.complaint import (
    CLOSED_STATUSES,
    Analysis,
    Assignment,
    AssignmentMethod,
    Complaint,
    RuleHit,
    Status,
    TimelineEntry,
    TriageState,
)
from app.models.department import Department
from app.models.user import User
from app.services import assignment_service, complaint_service, triage

log = get_logger(__name__)

#: Candidate window for dedup (spec 5.5), and the hard cap on how many we score.
SAME_CLAIMANT_WINDOW_DAYS = 90
SAME_CATEGORY_WINDOW_DAYS = 7
MAX_CANDIDATES = 200
CLAIMANT_HISTORY_DAYS = 30


async def build_input(complaint: Complaint) -> TriageInput:
    departments = await Department.find(Department.active == True).to_list()  # noqa: E712
    candidates = await _dedup_candidates(complaint)
    prior_count, prior_open = await _claimant_history(complaint)

    return TriageInput(
        subject=complaint.subject,
        body=complaint.body,
        channel=str(complaint.channel),
        claimant_email=complaint.claimant.email,
        claimant_is_vip=complaint.claimant.is_vip,
        claimant_prior_count_30d=prior_count,
        claimant_prior_open=prior_open,
        attachment_count=len(complaint.attachments),
        departments=[
            DepartmentInfo(
                code=d.code, name=d.name, keywords=d.keywords, categories=d.categories
            )
            for d in departments
        ],
        recent_complaints=candidates,
    )


async def _dedup_candidates(complaint: Complaint) -> list[DedupCandidate]:
    """Same claimant in 90 days, OR same category in 7 days. Capped at 200."""
    now = datetime.now(UTC)
    clauses: list[dict[str, Any]] = []
    if complaint.claimant.email:
        clauses.append(
            {
                "claimant.email": complaint.claimant.email,
                "created_at": {"$gte": now - timedelta(days=SAME_CLAIMANT_WINDOW_DAYS)},
            }
        )
    if complaint.analysis.category:
        clauses.append(
            {
                "analysis.category": complaint.analysis.category,
                "created_at": {"$gte": now - timedelta(days=SAME_CATEGORY_WINDOW_DAYS)},
            }
        )
    if not clauses:
        clauses.append(
            {"created_at": {"$gte": now - timedelta(days=SAME_CATEGORY_WINDOW_DAYS)}}
        )

    rows = (
        await Complaint.find({"$or": clauses, "_id": {"$ne": complaint.id}})
        .sort("-created_at")
        .limit(MAX_CANDIDATES)
        .to_list()
    )
    return [
        DedupCandidate(
            id=str(row.id),
            subject=row.subject,
            normalized_text=row.normalized_text or row.body,
            created_at=row.created_at,
            claimant_email=row.claimant.email,
        )
        for row in rows
    ]


async def _claimant_history(complaint: Complaint) -> tuple[int, int]:
    if not complaint.claimant.email:
        return 0, 0
    since = datetime.now(UTC) - timedelta(days=CLAIMANT_HISTORY_DAYS)
    base = {"claimant.email": complaint.claimant.email, "_id": {"$ne": complaint.id}}
    total = await Complaint.find({**base, "created_at": {"$gte": since}}).count()
    still_open = await Complaint.find(
        {**base, "status": {"$nin": [str(s) for s in CLOSED_STATUSES]}}
    ).count()
    return total, still_open


async def triage_complaint(complaint: Complaint) -> Complaint:
    """Run the pipeline and apply the outcome. Never raises into the worker."""
    engine = triage.get_engine()
    try:
        data = await build_input(complaint)
        output, suggestions = await pipeline.run(engine, data)
    except Exception as exc:  # noqa: BLE001 — a failed triage must not lose the complaint
        log.error("triage.failed", ref=complaint.ref, error=str(exc))
        await complaint_service.mark_triage_failed(complaint, "engine_error")
        await AnalysisTrace(
            complaint_id=complaint.id,
            complaint_ref=complaint.ref,
            engine=getattr(engine, "name", "unknown"),
            model_version="unknown",
            outcome="failed",
            error=str(exc),
        ).insert()
        return complaint

    # ---- decide (spec 5.6) -------------------------------------------------
    reason = output.triage_reason
    needs_human = output.needs_human_triage
    department_code = output.department_code

    if output.category and output.category not in ALL_CATEGORIES:
        department_code, needs_human, reason = (
            GENERAL_DEPARTMENT_CODE, True, "unknown_category",
        )

    department = await Department.find_one(Department.code == department_code)
    if department is None:
        department = await Department.find_one(
            Department.code == GENERAL_DEPARTMENT_CODE
        )
        needs_human, reason = True, "unknown_department"

    complaint.analysis = Analysis(
        category=output.category,
        category_confidence=output.category_confidence,
        category_alternatives=output.category_alternatives,
        subcategory=output.subcategory,
        priority=output.priority,
        priority_score=output.priority_score,
        rule_hits=[
            RuleHit(code=h.code, label=h.label, weight=h.weight, matched=h.matched)
            for h in output.rule_hits
        ],
        sentiment=output.sentiment,  # type: ignore[arg-type]
        sentiment_score=output.sentiment_score,
        urgency_score=output.urgency_score,
        language=output.language,
        keywords=output.keywords,
        duplicate_of=(
            PydanticObjectId(output.duplicate_of_id) if output.duplicate_of_id else None
        ),
        duplicate_score=output.duplicate_score,
        related_ids=[PydanticObjectId(i) for i in output.related_ids],
        needs_human_triage=needs_human,
        triage_reason=reason,
        engine=output.engine,
        model_version=output.model_version,
        latency_ms=output.latency_ms,
        analyzed_at=datetime.now(UTC),
    )
    complaint.normalized_text = output.normalized_text
    complaint.triage_state = TriageState.DONE
    if complaint.status is Status.NEW:
        complaint.status = Status.TRIAGED

    _apply_sla(complaint, department, output.priority)

    complaint.assignment = complaint.assignment or Assignment()
    complaint.assignment.department_id = department.id if department else None
    complaint.assignment.department_code = department.code if department else None
    complaint.assignment.method = AssignmentMethod.AUTO

    entries = [
        TimelineEntry(
            action="triage.completed",
            actor_type="engine",
            meta={
                "engine": output.engine,
                "model_version": output.model_version,
                "category": output.category,
                "confidence": output.category_confidence,
                "priority": output.priority,
                "latency_ms": output.latency_ms,
            },
        )
    ]
    if output.duplicate_of_id:
        # Flagged only. Auto-closing a duplicate is never allowed (spec 5.5).
        entries.append(
            TimelineEntry(
                action="duplicate.detected",
                actor_type="engine",
                meta={
                    "duplicate_of": output.duplicate_of_id,
                    "score": output.duplicate_score,
                },
            )
        )

    # Targeted write: a claimant may have attached a file while the pipeline was
    # running, and a whole-document save would have thrown it away.
    await complaint_service.persist_fields(
        complaint,
        {
            "analysis": complaint.analysis.model_dump(),
            "normalized_text": complaint.normalized_text,
            "triage_state": str(complaint.triage_state),
            "status": str(complaint.status),
            "sla": complaint.sla.model_dump(),
            "assignment": complaint.assignment.model_dump()
            if complaint.assignment
            else None,
        },
        entries,
    )

    agent = await _auto_assign(complaint, department, output.category, needs_human)

    await AnalysisTrace(
        complaint_id=complaint.id,
        complaint_ref=complaint.ref,
        engine=output.engine,
        model_version=output.model_version,
        stages=[TraceStage(**stage) for stage in output.stages],
        total_latency_ms=output.latency_ms,
        outcome="ok",
    ).insert()

    payload = complaint_service.event_payload(
        complaint,
        engine=output.engine,
        confidence=output.category_confidence,
        needs_human_triage=needs_human,
        triage_reason=reason,
        duplicate_of=output.duplicate_of_id,
        suggested_duplicates=[m.candidate_id for m in suggestions],
    )
    await publish(EventName.COMPLAINT_TRIAGED, payload)
    if agent is not None:
        await publish(
            EventName.COMPLAINT_ASSIGNED,
            {**payload, "agent_id": str(agent.id), "agent_email": agent.email},
        )

    log.info(
        "triage.done", ref=complaint.ref, category=output.category,
        priority=output.priority, engine=output.engine,
        latency_ms=output.latency_ms, needs_human=needs_human,
    )
    return complaint


def _apply_sla(complaint: Complaint, department: Department | None, priority: int) -> None:
    hours = settings.sla_hours_by_priority.get(priority, settings.sla_hours_p3)
    if department is not None and department.default_sla_hours:
        hours = department.default_sla_hours
    complaint.sla.hours = hours
    complaint.sla.due_at = complaint.created_at + timedelta(hours=hours)
    complaint.sla.breached = False
    complaint.sla.warned = False


async def _auto_assign(
    complaint: Complaint,
    department: Department | None,
    category: str | None,
    needs_human: bool,
) -> User | None:
    """Assign an agent unless the complaint needs a human triage decision first."""
    assignment = complaint.assignment or Assignment()
    complaint.assignment = assignment

    if department is None or needs_human:
        assignment.method = AssignmentMethod.QUEUE
        await complaint_service.persist_fields(
            complaint, {"assignment": assignment.model_dump()}
        )
        return None

    agent = await assignment_service.pick_agent(department, category)
    if agent is None:
        assignment.method = AssignmentMethod.QUEUE
        await complaint_service.persist_fields(
            complaint,
            {"assignment": assignment.model_dump()},
            [
                TimelineEntry(
                    action="assignment.queued",
                    actor_type="system",
                    meta={"department": department.code},
                )
            ],
        )
        return None

    assignment.agent_id = agent.id
    assignment.assigned_at = datetime.now(UTC)
    assignment.method = AssignmentMethod.AUTO
    complaint.status = Status.ASSIGNED
    await complaint_service.persist_fields(
        complaint,
        {
            "assignment": assignment.model_dump(),
            "status": str(Status.ASSIGNED),
        },
        [
            TimelineEntry(
                action="assignment.auto",
                actor_type="system",
                meta={"agent_id": str(agent.id), "department": department.code},
            )
        ],
    )
    return agent

"""SLA computation, warnings, breaches and escalation.

Two clocks are supported. Wall-clock is the default and is what the demo uses,
because "4 hours" reading as four hours is easier to follow. Business-hours mode
uses the Tunisian working calendar so a Friday-evening complaint is not breached
before anyone could have opened it.
"""

from datetime import UTC, datetime, timedelta

from app.config import settings
from app.core.logging import get_logger
from app.domain.calendar_tn import add_business_hours, business_seconds_between
from app.events.bus import publish
from app.events.types import EventName
from app.models.complaint import CLOSED_STATUSES, Complaint
from app.models.department import Department
from app.models.user import User
from app.services import complaint_service

log = get_logger(__name__)

#: Warn once this share of the budget is consumed (spec 4.3).
WARNING_RATIO = 0.80
#: Safety valve so one sweep cannot melt the box on a huge backlog.
SWEEP_LIMIT = 500


def hours_for_priority(priority: int | None) -> int:
    return settings.sla_hours_by_priority.get(
        priority or 3, settings.sla_hours_p3
    )


def due_at(start: datetime, hours: int) -> datetime:
    if settings.sla_business_hours:
        return add_business_hours(start, hours)
    return start + timedelta(hours=hours)


def consumed_ratio(complaint: Complaint, now: datetime | None = None) -> float:
    """Share of the SLA budget used, 0..n. Above 1.0 means breached."""
    moment = now or datetime.now(UTC)
    budget_hours = complaint.sla.hours or hours_for_priority(complaint.analysis.priority)
    if budget_hours <= 0:
        return 0.0

    if settings.sla_business_hours:
        elapsed = business_seconds_between(complaint.created_at, moment)
    else:
        elapsed = (moment - complaint.created_at).total_seconds()
    return elapsed / (budget_hours * 3600)


async def sweep(now: datetime | None = None) -> dict[str, int]:
    """Find complaints that crossed 80% or blew their deadline and act once."""
    moment = now or datetime.now(UTC)
    open_complaints = (
        await Complaint.find(
            {
                "status": {"$nin": [str(s) for s in CLOSED_STATUSES]},
                "sla.due_at": {"$ne": None},
            }
        )
        .sort("sla.due_at")
        .limit(SWEEP_LIMIT)
        .to_list()
    )

    warned = breached = escalated = 0
    for complaint in open_complaints:
        ratio = consumed_ratio(complaint, moment)

        if ratio >= 1.0 and not complaint.sla.breached:
            await _mark_breached(complaint, moment)
            breached += 1
            if await _escalate(complaint):
                escalated += 1
        elif ratio >= WARNING_RATIO and not complaint.sla.warned:
            await _mark_warned(complaint, ratio)
            warned += 1

    if warned or breached:
        log.info("sla.sweep", warned=warned, breached=breached, escalated=escalated,
                 scanned=len(open_complaints))
    return {
        "scanned": len(open_complaints), "warned": warned,
        "breached": breached, "escalated": escalated,
    }


async def _mark_warned(complaint: Complaint, ratio: float) -> None:
    complaint.sla.warned = True
    complaint.log("sla.warning", actor_type="system", consumed=round(ratio, 3))
    complaint.touch()
    await complaint.save()
    await publish(
        EventName.SLA_WARNING,
        await _payload(complaint, consumed=round(ratio, 3)),
    )


async def _mark_breached(complaint: Complaint, moment: datetime) -> None:
    complaint.sla.breached = True
    complaint.sla.warned = True
    complaint.log(
        "sla.breached", actor_type="system",
        due_at=complaint.sla.due_at.isoformat() if complaint.sla.due_at else None,
    )
    complaint.touch()
    await complaint.save()
    await publish(EventName.SLA_BREACHED, await _payload(complaint))


async def _escalate(complaint: Complaint) -> bool:
    """Escalate to the department's escalation contact, once per level."""
    if complaint.assignment is None or complaint.assignment.department_id is None:
        return False
    department = await Department.get(complaint.assignment.department_id)
    if department is None or department.escalation_to is None:
        return False

    complaint.sla.escalation_level += 1
    complaint.log(
        "complaint.escalated", actor_type="system",
        level=complaint.sla.escalation_level, to=str(department.escalation_to),
    )
    complaint.touch()
    await complaint.save()

    supervisor = await User.get(department.escalation_to)
    await publish(
        EventName.ESCALATED,
        await _payload(
            complaint,
            level=complaint.sla.escalation_level,
            reason="sla_breached",
            escalation_email=supervisor.email if supervisor else None,
        ),
    )
    return True


async def _payload(complaint: Complaint, **extra: object) -> dict:
    agent_email = None
    if complaint.assignment and complaint.assignment.agent_id:
        agent = await User.get(complaint.assignment.agent_id)
        agent_email = agent.email if agent else None
    return complaint_service.event_payload(
        complaint, agent_email=agent_email, **extra
    )

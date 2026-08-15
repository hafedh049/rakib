"""Complaint lifecycle: creation, RBAC-scoped listing, updates, messages.

The triage decision rules of spec 5.6 live here rather than in the engine, so the
engine stays a pure function of text and the policy stays where policy belongs.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from beanie import PydanticObjectId

from app.config import settings
from app.core.background import spawn
from app.core.errors import Conflict, NotFound, PermissionDenied, ValidationError
from app.core.logging import get_logger
from app.core.pagination import Page, clamp_limit, cursor_filter, encode_cursor
from app.core.security import create_tracking_token
from app.deps import department_scope
from app.domain.taxonomy import (
    ALL_CATEGORIES,
    GENERAL_DEPARTMENT_CODE,
    department_for_category,
)
from app.events.bus import publish
from app.events.types import EventName
from app.models.complaint import (
    CLOSED_STATUSES,
    Assignment,
    AssignmentMethod,
    Attachment,
    Claimant,
    Complaint,
    Message,
    Satisfaction,
    Status,
    TimelineEntry,
    TriageState,
)
from app.models.counter import next_complaint_ref
from app.models.department import Department
from app.models.user import Role, User, role_at_least
from app.schemas.complaint import ComplaintCreate, ComplaintPatch
from app.workers import queue

log = get_logger(__name__)

#: Until triage runs, a complaint gets the "normal" budget so it can never sit
#: on the SLA board with no clock at all. Triage overwrites this (spec 5.6).
PROVISIONAL_PRIORITY = 3


def event_payload(complaint: Complaint, **extra: Any) -> dict[str, Any]:
    """The shared shape every notifier reads. Kept flat so it survives JSON."""
    payload: dict[str, Any] = {
        "complaint_id": str(complaint.id),
        "ref": complaint.ref,
        "subject": complaint.subject,
        "status": str(complaint.status),
        "channel": str(complaint.channel),
        "priority": complaint.analysis.priority,
        "category": complaint.analysis.category,
        "claimant_name": complaint.claimant.full_name,
        "claimant_email": complaint.claimant.email,
        "department": (
            complaint.assignment.department_code if complaint.assignment else None
        ),
        "due_at": complaint.sla.due_at.isoformat() if complaint.sla.due_at else None,
    }
    payload.update(extra)
    return payload


# ------------------------------------------------------------------------- creation
async def create_complaint(
    payload: ComplaintCreate, actor: User | None = None
) -> tuple[Complaint, str]:
    """Create a complaint and return it with its signed tracking URL."""
    claimant = Claimant(
        user_id=actor.id if actor and Role(actor.role) is Role.CLAIMANT else None,
        full_name=payload.claimant.full_name.strip(),
        email=(payload.claimant.email or "").lower() or None,
        phone=payload.claimant.phone,
        external_id=payload.claimant.external_id,
    )

    complaint = Complaint(
        ref=await next_complaint_ref(),
        channel=payload.channel,
        claimant=claimant,
        subject=payload.subject.strip(),
        body=payload.body.strip(),
    )
    complaint.sla.hours = settings.sla_hours_by_priority[PROVISIONAL_PRIORITY]
    complaint.sla.due_at = complaint.created_at + timedelta(hours=complaint.sla.hours)
    complaint.log(
        "complaint.created",
        actor_type="user" if actor else "system",
        actor_id=str(actor.id) if actor else None,
        channel=str(payload.channel),
    )
    await complaint.insert()

    url = tracking_url(complaint)
    # Both are best-effort and their results are ignored, so they run after the
    # response rather than adding two Redis round trips to the claimant's wait.
    payload_for_event = event_payload(complaint, tracking_url=url)
    spawn(
        queue.enqueue("triage_complaint", str(complaint.id)),
        name=f"enqueue-triage:{complaint.ref}",
    )
    spawn(
        publish(EventName.COMPLAINT_CREATED, payload_for_event),
        name=f"publish-created:{complaint.ref}",
    )
    log.info(
        "complaint.created", ref=complaint.ref, channel=str(payload.channel),
        authenticated=actor is not None,
    )
    return complaint, url


def tracking_url(complaint: Complaint) -> str:
    token = create_tracking_token(str(complaint.id), scope="track")
    return f"{settings.public_url}/portal/suivi?token={token}"


def satisfaction_url(complaint: Complaint) -> str:
    token = create_tracking_token(str(complaint.id), scope="satisfaction")
    return f"{settings.public_url}/portal/satisfaction?token={token}"


# -------------------------------------------------------------------------- reading
async def list_complaints(
    user: User,
    *,
    status: list[Status] | None = None,
    category: str | None = None,
    priority: int | None = None,
    department_code: str | None = None,
    agent_id: PydanticObjectId | None = None,
    q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sla_breached: bool | None = None,
    needs_human_triage: bool | None = None,
    unassigned: bool | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> Page[Complaint]:
    """List complaints the caller is allowed to see.

    The RBAC scope is merged into the query itself — never applied after fetch —
    so a claimant literally cannot page into another claimant's rows.
    """
    page_size = clamp_limit(limit)
    conditions: list[dict[str, Any]] = [department_scope(user)]

    if status:
        conditions.append({"status": {"$in": [str(s) for s in status]}})
    if category:
        conditions.append({"analysis.category": category})
    if priority is not None:
        conditions.append({"analysis.priority": priority})
    if department_code:
        conditions.append({"assignment.department_code": department_code})
    if agent_id is not None:
        conditions.append({"assignment.agent_id": agent_id})
    if sla_breached is not None:
        conditions.append({"sla.breached": sla_breached})
    if needs_human_triage is not None:
        conditions.append({"analysis.needs_human_triage": needs_human_triage})
    if unassigned:
        conditions.append({"assignment.agent_id": None})
    if date_from or date_to:
        window: dict[str, Any] = {}
        if date_from:
            window["$gte"] = date_from
        if date_to:
            window["$lte"] = date_to
        conditions.append({"created_at": window})
    if q:
        conditions.append({"$text": {"$search": q}})

    cursor_condition = cursor_filter(cursor)
    if cursor_condition:
        conditions.append(cursor_condition)

    query = {"$and": [c for c in conditions if c]} if any(conditions) else {}

    rows = (
        await Complaint.find(query)
        .sort("-created_at", "-_id")
        .limit(page_size + 1)
        .to_list()
    )

    has_more = len(rows) > page_size
    items = rows[:page_size]
    next_cursor = (
        encode_cursor(items[-1].created_at, items[-1].id)
        if has_more and items and items[-1].id
        else None
    )
    return Page(items=items, next_cursor=next_cursor, has_more=has_more)


async def get_for_user(complaint_id: PydanticObjectId, user: User) -> Complaint:
    """Fetch one complaint, enforcing the same scope the list query uses."""
    scope = department_scope(user)
    query: dict[str, Any] = {"_id": complaint_id}
    if scope:
        query = {"$and": [{"_id": complaint_id}, scope]}
    complaint = await Complaint.find_one(query)
    if complaint is None:
        # 404 rather than 403: an out-of-scope complaint must not be
        # distinguishable from a non-existent one.
        raise NotFound("Reclamation introuvable")
    return complaint


async def get_by_ref(ref: str) -> Complaint:
    complaint = await Complaint.find_one(Complaint.ref == ref)
    if complaint is None:
        raise NotFound("Reclamation introuvable")
    return complaint


# ------------------------------------------------------------------------- mutation
async def patch_complaint(
    complaint: Complaint, payload: ComplaintPatch, actor: User
) -> Complaint:
    """Apply a staff edit. Category/department changes emit a training signal."""
    changed: dict[str, Any] = {}

    if payload.status is not None and payload.status != complaint.status:
        _guard_status_transition(complaint, payload.status, actor)
        changed["status"] = (str(complaint.status), str(payload.status))
        complaint.status = payload.status
        if payload.status in CLOSED_STATUSES:
            complaint.sla.resolved_at = datetime.now(UTC)

    if payload.priority is not None and payload.priority != complaint.analysis.priority:
        if not role_at_least(actor.role, Role.SUPERVISOR):
            raise PermissionDenied("Seul un superviseur peut changer la priorite")
        changed["priority"] = (complaint.analysis.priority, payload.priority)
        complaint.analysis.priority = payload.priority
        _apply_sla_for_priority(complaint, payload.priority)

    if payload.category is not None and payload.category != complaint.analysis.category:
        if payload.category not in ALL_CATEGORIES:
            raise ValidationError(f"Categorie inconnue: {payload.category}")
        changed["category"] = (complaint.analysis.category, payload.category)
        complaint.analysis.category = payload.category
        complaint.corrected = True

    if payload.department_code is not None:
        department = await Department.find_one(
            Department.code == payload.department_code
        )
        if department is None:
            raise ValidationError(f"Departement inconnu: {payload.department_code}")
        current = complaint.assignment.department_code if complaint.assignment else None
        if current != department.code:
            changed["department"] = (current, department.code)
            complaint.corrected = True
        await _assign_department(complaint, department, method=AssignmentMethod.MANUAL)

    if payload.agent_id is not None:
        if not role_at_least(actor.role, Role.SUPERVISOR):
            raise PermissionDenied("Seul un superviseur peut reaffecter")
        agent = await User.get(payload.agent_id)
        if agent is None or not agent.is_staff:
            raise ValidationError("Agent invalide")
        changed["agent"] = (
            str(complaint.assignment.agent_id) if complaint.assignment else None,
            str(agent.id),
        )
        complaint.assignment = complaint.assignment or Assignment()
        complaint.assignment.agent_id = agent.id
        complaint.assignment.assigned_at = datetime.now(UTC)
        complaint.assignment.method = AssignmentMethod.MANUAL
        if complaint.status is Status.NEW:
            complaint.status = Status.ASSIGNED

    if payload.is_vip is not None and payload.is_vip != complaint.claimant.is_vip:
        changed["is_vip"] = (complaint.claimant.is_vip, payload.is_vip)
        complaint.claimant.is_vip = payload.is_vip

    if not changed:
        return complaint

    complaint.log(
        "complaint.updated",
        actor_type="agent",
        actor_id=str(actor.id),
        **{key: {"from": old, "to": new} for key, (old, new) in changed.items()},
    )
    complaint.touch()
    await complaint.save()

    await publish(
        EventName.COMPLAINT_UPDATED,
        event_payload(complaint, changed=list(changed), actor_id=str(actor.id)),
    )
    if "category" in changed or "department" in changed:
        # A human disagreed with the engine. The `corrected` flag drives the
        # correction rate in the KPI report; the event lets the console react.
        await publish(
            EventName.TRIAGE_CORRECTED,
            event_payload(
                complaint,
                previous_category=changed.get("category", (None, None))[0],
                new_category=complaint.analysis.category,
                corrected_by=str(actor.id),
            ),
        )
    log.info("complaint.updated", ref=complaint.ref, fields=list(changed))
    return complaint


def _guard_status_transition(
    complaint: Complaint, target: Status, actor: User
) -> None:
    if complaint.status in CLOSED_STATUSES and target not in CLOSED_STATUSES:
        if not role_at_least(actor.role, Role.SUPERVISOR):
            raise PermissionDenied(
                "Seul un superviseur peut rouvrir une reclamation cloturee"
            )


def _apply_sla_for_priority(complaint: Complaint, priority: int) -> None:
    hours = settings.sla_hours_by_priority.get(priority, settings.sla_hours_p3)
    complaint.sla.hours = hours
    complaint.sla.due_at = complaint.created_at + timedelta(hours=hours)
    complaint.sla.breached = False
    complaint.sla.warned = False


async def _assign_department(
    complaint: Complaint, department: Department, method: AssignmentMethod
) -> None:
    complaint.assignment = complaint.assignment or Assignment()
    if complaint.assignment.department_code != department.code:
        # Moving department drops the agent — the old one no longer owns it.
        complaint.assignment.agent_id = None
    complaint.assignment.department_id = department.id
    complaint.assignment.department_code = department.code
    complaint.assignment.method = method
    if department.default_sla_hours:
        complaint.sla.hours = department.default_sla_hours
        complaint.sla.due_at = complaint.created_at + timedelta(
            hours=department.default_sla_hours
        )


async def route_to_category_department(complaint: Complaint, category: str | None) -> None:
    """Route by category, falling back to GENERAL when unknown (spec 5.6)."""
    code = department_for_category(category)
    department = await Department.find_one(Department.code == code)
    if department is None:
        department = await Department.find_one(
            Department.code == GENERAL_DEPARTMENT_CODE
        )
    if department is not None:
        await _assign_department(complaint, department, AssignmentMethod.AUTO)


# ------------------------------------------------------------------------- messages
async def _append(
    complaint: Complaint, pushes: dict[str, Any], sets: dict[str, Any] | None = None
) -> None:
    """Append to arrays with `$push` instead of rewriting the whole document.

    Beanie's `save()` replaces the entire document with the in-memory copy. A
    worker that fetched the complaint a second earlier will therefore wipe
    anything appended in between — messages and attachments both went missing
    this way while triage was in flight. `$push` touches only the array.
    """
    now = datetime.now(UTC)
    complaint.updated_at = now
    await complaint.get_motor_collection().update_one(
        {"_id": complaint.id},
        {"$push": pushes, "$set": {"updated_at": now, **(sets or {})}},
    )


async def persist_fields(
    complaint: Complaint,
    fields: dict[str, Any],
    timeline: list[TimelineEntry] | None = None,
) -> None:
    """Write only the fields the caller owns, and append timeline entries.

    Used by triage, which runs concurrently with whatever a claimant or agent is
    doing. A whole-document save here silently discarded attachments and
    messages added while the pipeline was running.
    """
    now = datetime.now(UTC)
    complaint.updated_at = now
    update: dict[str, Any] = {"$set": {**fields, "updated_at": now}}
    if timeline:
        complaint.timeline.extend(timeline)
        update["$push"] = {
            "timeline": {"$each": [entry.model_dump() for entry in timeline]}
        }
    await complaint.get_motor_collection().update_one({"_id": complaint.id}, update)


async def add_message(
    complaint: Complaint, body: str, author: User, internal: bool = False
) -> Message:
    message = Message(
        author_type="agent" if author.is_staff else "claimant",
        author_id=author.id,
        author_name=author.full_name,
        body=body.strip(),
        internal=internal,
    )
    entry = TimelineEntry(
        action="message.internal" if internal else "message.reply",
        actor_type="agent" if author.is_staff else "user",
        actor_id=str(author.id),
    )

    sets: dict[str, Any] = {}
    if not internal and complaint.status is Status.ASSIGNED:
        complaint.status = Status.IN_PROGRESS
        sets["status"] = str(Status.IN_PROGRESS)

    complaint.messages.append(message)
    complaint.timeline.append(entry)
    await _append(
        complaint,
        {"messages": message.model_dump(), "timeline": entry.model_dump()},
        sets,
    )

    if not internal:
        await publish(
            EventName.COMPLAINT_REPLIED,
            event_payload(
                complaint, message=message.body, tracking_url=tracking_url(complaint)
            ),
        )
    return message


async def add_attachment(complaint: Complaint, attachment: Attachment) -> Attachment:
    entry = TimelineEntry(
        action="attachment.added",
        actor_type="user",
        actor_id=str(attachment.uploaded_by) if attachment.uploaded_by else None,
        meta={"filename": attachment.filename, "size": attachment.size},
    )
    complaint.attachments.append(attachment)
    complaint.timeline.append(entry)
    await _append(
        complaint,
        {"attachments": attachment.model_dump(), "timeline": entry.model_dump()},
    )
    return attachment


async def resolve(complaint: Complaint, resolution: str, actor: User) -> Complaint:
    if complaint.status in CLOSED_STATUSES:
        raise Conflict("Reclamation deja cloturee")
    await add_message(complaint, resolution, actor, internal=False)
    complaint.status = Status.RESOLVED
    complaint.sla.resolved_at = datetime.now(UTC)
    complaint.log("complaint.resolved", actor_type="agent", actor_id=str(actor.id))
    complaint.touch()
    await complaint.save()

    await publish(
        EventName.COMPLAINT_RESOLVED,
        event_payload(
            complaint,
            resolution=resolution,
            satisfaction_url=satisfaction_url(complaint),
        ),
    )
    return complaint


async def submit_satisfaction(
    complaint: Complaint, score: int, comment: str | None
) -> Complaint:
    if complaint.satisfaction is not None:
        raise Conflict("Une evaluation a deja ete enregistree")
    if complaint.status not in CLOSED_STATUSES:
        raise Conflict("La reclamation n'est pas encore resolue")
    complaint.satisfaction = Satisfaction(score=score, comment=comment)
    complaint.log("satisfaction.submitted", actor_type="user", score=score)
    complaint.touch()
    await complaint.save()
    return complaint


async def mark_triage_failed(complaint: Complaint, reason: str) -> None:
    complaint.triage_state = TriageState.FAILED
    complaint.analysis.needs_human_triage = True
    complaint.analysis.triage_reason = reason
    complaint.log("triage.failed", actor_type="engine", reason=reason)
    complaint.touch()
    await complaint.save()

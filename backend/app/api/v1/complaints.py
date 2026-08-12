from datetime import datetime
from typing import Annotated
from uuid import uuid4

from beanie import PydanticObjectId
from fastapi import APIRouter, File, Query, UploadFile, status

from app.config import settings
from app.core.errors import NotFound, PermissionDenied, ValidationError
from app.core.ids import doc_id
from app.core.pagination import Page
from app.core.security import verify_tracking_token
from app.deps import AgentUser, CurrentUser, OptionalUser
from app.models.complaint import Attachment, Complaint, Status
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintCreated,
    ComplaintListItem,
    ComplaintOut,
    ComplaintPatch,
    ComplaintPublicOut,
    MessageCreate,
    PublicMessage,
    ResolveRequest,
    SatisfactionIn,
)
from app.services import complaint_service, storage

router = APIRouter(prefix="/complaints", tags=["complaints"])


# --------------------------------------------------------------------------- public
@router.post("", response_model=ComplaintCreated, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    payload: ComplaintCreate, actor: OptionalUser
) -> ComplaintCreated:
    """Submit a complaint. Open to anonymous claimants and to signed-in users.

    Returns in well under 100 ms: triage runs in the worker (spec section 9).
    """
    complaint, url = await complaint_service.create_complaint(payload, actor)
    return ComplaintCreated(
        id=doc_id(complaint),
        ref=complaint.ref,
        status=complaint.status,
        tracking_url=url,
        created_at=complaint.created_at,
    )


@router.get("/track", response_model=ComplaintPublicOut)
async def track(token: Annotated[str, Query()]) -> ComplaintPublicOut:
    """Public tracking via a signed, complaint-scoped token.

    Deliberately NOT `GET /complaints/{ref}`: the ref is sequential, so tracking
    by ref would let anyone enumerate every complaint in the system.
    """
    complaint = await _complaint_from_token(token, scope="track")
    return _to_public(complaint)


@router.post("/satisfaction", response_model=ComplaintPublicOut)
async def submit_satisfaction(
    payload: SatisfactionIn, token: Annotated[str, Query()]
) -> ComplaintPublicOut:
    complaint = await _complaint_from_token(token, scope="satisfaction")
    complaint = await complaint_service.submit_satisfaction(
        complaint, payload.score, payload.comment
    )
    return _to_public(complaint)


# ---------------------------------------------------------------------------- staff
@router.get("", response_model=Page[ComplaintListItem])
async def list_complaints(
    user: CurrentUser,
    status_filter: Annotated[list[Status] | None, Query(alias="status")] = None,
    category: Annotated[str | None, Query()] = None,
    priority: Annotated[int | None, Query(ge=1, le=4)] = None,
    department: Annotated[str | None, Query()] = None,
    agent_id: Annotated[PydanticObjectId | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    sla_breached: Annotated[bool | None, Query()] = None,
    needs_human_triage: Annotated[bool | None, Query()] = None,
    unassigned: Annotated[bool | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> Page[ComplaintListItem]:
    page = await complaint_service.list_complaints(
        user,
        status=status_filter,
        category=category,
        priority=priority,
        department_code=department,
        agent_id=agent_id,
        q=q,
        date_from=date_from,
        date_to=date_to,
        sla_breached=sla_breached,
        needs_human_triage=needs_human_triage,
        unassigned=unassigned,
        cursor=cursor,
        limit=limit,
    )
    return Page[ComplaintListItem](
        items=[_to_list_item(c) for c in page.items],
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{complaint_id}", response_model=ComplaintOut)
async def get_complaint(complaint_id: PydanticObjectId, user: CurrentUser) -> Complaint:
    complaint = await complaint_service.get_for_user(complaint_id, user)
    if not user.is_staff:
        # A signed-in claimant sees their own complaint without internal notes.
        complaint.messages = [m for m in complaint.messages if not m.internal]
    return complaint


@router.patch("/{complaint_id}", response_model=ComplaintOut)
async def patch_complaint(
    complaint_id: PydanticObjectId, payload: ComplaintPatch, user: AgentUser
) -> Complaint:
    complaint = await complaint_service.get_for_user(complaint_id, user)
    return await complaint_service.patch_complaint(complaint, payload, user)


@router.post(
    "/{complaint_id}/messages", response_model=ComplaintOut, status_code=201
)
async def add_message(
    complaint_id: PydanticObjectId, payload: MessageCreate, user: CurrentUser
) -> Complaint:
    complaint = await complaint_service.get_for_user(complaint_id, user)
    if payload.internal and not user.is_staff:
        raise PermissionDenied("Note interne reservee au personnel")
    await complaint_service.add_message(
        complaint, payload.body, user, internal=payload.internal
    )
    return complaint


@router.post("/{complaint_id}/resolve", response_model=ComplaintOut)
async def resolve_complaint(
    complaint_id: PydanticObjectId, payload: ResolveRequest, user: AgentUser
) -> Complaint:
    complaint = await complaint_service.get_for_user(complaint_id, user)
    return await complaint_service.resolve(complaint, payload.resolution, user)


@router.post(
    "/{complaint_id}/attachments", response_model=ComplaintOut, status_code=201
)
async def upload_attachment(
    complaint_id: PydanticObjectId,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
) -> Complaint:
    complaint = await complaint_service.get_for_user(complaint_id, user)

    content_type = file.content_type or "application/octet-stream"
    if content_type not in storage.ALLOWED_CONTENT_TYPES:
        raise ValidationError(f"Type de fichier non autorise: {content_type}")

    data = await file.read()
    max_bytes = settings.max_attachment_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise ValidationError(
            f"Fichier trop volumineux (maximum {settings.max_attachment_mb} Mo)"
        )

    key = f"{complaint.ref}/{uuid4().hex}-{file.filename}"
    await storage.put_object(key, data, content_type)
    await complaint_service.add_attachment(
        complaint,
        Attachment(
            filename=file.filename or "piece-jointe",
            content_type=content_type,
            size=len(data),
            s3_key=key,
            uploaded_by=user.id,
        ),
    )
    return complaint


@router.get("/{complaint_id}/attachments/{attachment_id}")
async def attachment_url(
    complaint_id: PydanticObjectId, attachment_id: str, user: CurrentUser
) -> dict[str, str]:
    """Hand out a short-lived presigned URL rather than proxying the bytes."""
    complaint = await complaint_service.get_for_user(complaint_id, user)
    attachment = next(
        (a for a in complaint.attachments if a.id == attachment_id), None
    )
    if attachment is None:
        raise NotFound("Piece jointe introuvable")
    return {"url": await storage.presigned_url(attachment.s3_key)}


# ------------------------------------------------------------------------- helpers
async def _complaint_from_token(token: str, scope: str) -> Complaint:
    complaint_id = verify_tracking_token(token, scope=scope)
    complaint = await Complaint.get(PydanticObjectId(complaint_id))
    if complaint is None:
        raise NotFound("Reclamation introuvable")
    return complaint


def _to_public(complaint: Complaint) -> ComplaintPublicOut:
    return ComplaintPublicOut(
        ref=complaint.ref,
        subject=complaint.subject,
        body=complaint.body,
        status=complaint.status,
        channel=complaint.channel,
        department=complaint.assignment.department_code if complaint.assignment else None,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
        sla_due_at=complaint.sla.due_at,
        messages=[
            PublicMessage(
                at=m.at,
                author_type=m.author_type,
                author_name=m.author_name if m.author_type != "agent" else None,
                body=m.body,
            )
            for m in complaint.messages
            if not m.internal
        ],
        satisfaction_submitted=complaint.satisfaction is not None,
    )


def _to_list_item(complaint: Complaint) -> ComplaintListItem:
    return ComplaintListItem(
        id=doc_id(complaint),
        ref=complaint.ref,
        subject=complaint.subject,
        channel=complaint.channel,
        status=complaint.status,
        triage_state=complaint.triage_state,
        claimant=complaint.claimant,
        analysis=complaint.analysis,
        assignment=complaint.assignment,
        sla_due_at=complaint.sla.due_at,
        sla_breached=complaint.sla.breached,
        sla_warned=complaint.sla.warned,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
    )

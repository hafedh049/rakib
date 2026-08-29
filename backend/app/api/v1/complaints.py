from datetime import datetime
from typing import Annotated, Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from app.core.errors import (
    NotFound,
    PermissionDenied,
)
from app.core.ids import doc_id
from app.core.pagination import Page
from app.core.security import verify_tracking_token
from app.deps import AgentUser, CurrentUser, OptionalUser, SupervisorUser
from app.models.complaint import Complaint, Status
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
)
from app.services import complaint_service, triage_service

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


async def _complaint_from_token(token: str, scope: str) -> Complaint:
    """Resolve a signed tracking token to its complaint, or refuse.

    The token is complaint-scoped and signed, so it grants access to exactly
    one record and nothing else — an anonymous claimant has no session.
    """
    complaint_id = verify_tracking_token(token, scope=scope)
    complaint = await Complaint.get(complaint_id)
    if complaint is None:
        raise NotFound("Reclamation introuvable")
    return complaint


@router.get("/track", response_model=ComplaintPublicOut)
async def track(token: Annotated[str, Query()]) -> ComplaintPublicOut:
    """Public tracking via a signed, complaint-scoped token.

    Deliberately NOT `GET /complaints/{ref}`: the ref is sequential, so tracking
    by ref would let anyone enumerate every complaint in the system.
    """
    complaint = await _complaint_from_token(token, scope="track")
    return _to_public(complaint)


@router.get("", response_model=Page[ComplaintListItem])
async def list_complaints(
    user: CurrentUser,
    status_filter: Annotated[list[Status] | None, Query(alias="status")] = None,
    category: Annotated[str | None, Query()] = None,
    department: Annotated[str | None, Query()] = None,
    agent_id: Annotated[PydanticObjectId | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    needs_human_triage: Annotated[bool | None, Query()] = None,
    unassigned: Annotated[bool | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> Page[ComplaintListItem]:
    page = await complaint_service.list_complaints(
        user,
        status=status_filter,
        category=category,
        department_code=department,
        agent_id=agent_id,
        q=q,
        date_from=date_from,
        date_to=date_to,
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


@router.post("/{complaint_id}/retriage", response_model=ComplaintOut)
async def retriage(complaint_id: PydanticObjectId, user: SupervisorUser) -> Complaint:
    """Re-run the whole pipeline. Synchronous so the caller sees the result."""
    complaint = await complaint_service.get_for_user(complaint_id, user)
    complaint.log("triage.requested", actor_type="agent", actor_id=str(user.id))
    return await triage_service.triage_complaint(complaint)


@router.get("/{complaint_id}/analysis")
async def analysis(complaint_id: PydanticObjectId, user: AgentUser) -> dict[str, Any]:
    """Everything behind the decision: the category, the terms that produced it,
    and the alternatives.

    This is the explainability surface — the panel an agent opens to ask why a
    complaint was routed to their queue, and the reason a lexicon was chosen
    over a model in the first place.
    """
    complaint = await complaint_service.get_for_user(complaint_id, user)
    return {
        "ref": complaint.ref,
        "triage_state": str(complaint.triage_state),
        "category": complaint.analysis.category,
        "analysis": complaint.analysis.model_dump(mode="json"),
    }


def _to_public(complaint: Complaint) -> ComplaintPublicOut:
    """The claimant's view. Internal notes never cross this boundary."""
    return ComplaintPublicOut(
        ref=complaint.ref,
        subject=complaint.subject,
        body=complaint.body,
        status=complaint.status,
        channel=complaint.channel,
        department=complaint.assignment.department_code if complaint.assignment else None,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
        messages=[
            PublicMessage(
                at=m.at,
                author_type=m.author_type,
                # The bank answers as the bank; naming the individual agent
                # invites a claimant to address them personally.
                author_name=m.author_name if m.author_type != "agent" else None,
                body=m.body,
            )
            for m in complaint.messages
            if not m.internal
        ],
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
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
    )

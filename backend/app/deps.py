"""Shared FastAPI dependencies: authentication and RBAC.

RBAC rule from the spec: scoping is enforced by injecting a filter into the query,
never by filtering after fetch. `department_scope()` returns that filter.
"""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from beanie import PydanticObjectId
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AuthenticationError, PermissionDenied
from app.core.security import decode_access_token
from app.models.user import Role, User, role_at_least

_bearer = HTTPBearer(auto_error=False)
_bearer_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise AuthenticationError()
    payload = decode_access_token(credentials.credentials)
    user = await User.get(PydanticObjectId(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthenticationError("Compte introuvable ou desactive")
    return user


async def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_optional)
    ],
) -> User | None:
    """For endpoints that accept both anonymous and authenticated callers."""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:  # noqa: BLE001 — a bad token on a public route means anonymous
        return None
    user = await User.get(PydanticObjectId(payload["sub"]))
    return user if user and user.is_active else None


def require_role(
    minimum: Role,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Admit `minimum` and every role above it (see ROLE_ORDER)."""

    async def _dependency(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not role_at_least(user.role, minimum):
            raise PermissionDenied(
                f"Role '{user.role}' insuffisant (minimum requis: '{minimum}')"
            )
        return user

    return _dependency


def require_exact_roles(
    *roles: Role,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    allowed = {Role(r) for r in roles}

    async def _dependency(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if Role(user.role) not in allowed:
            raise PermissionDenied(f"Role '{user.role}' non autorise")
        return user

    return _dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
AgentUser = Annotated[User, Depends(require_role(Role.AGENT))]
SupervisorUser = Annotated[User, Depends(require_role(Role.SUPERVISOR))]
AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]


def department_scope(user: User) -> dict[str, Any]:
    """Query filter implementing the §6 RBAC read matrix.

    supervisor/admin -> everything; agent -> own department; claimant -> own
    complaints. Returned as a Mongo filter so it composes into the query itself.
    """
    if role_at_least(user.role, Role.SUPERVISOR):
        return {}
    if Role(user.role) is Role.AGENT:
        if user.department_id is None:
            # An agent with no department can only see what is assigned to them.
            return {"assignment.agent_id": user.id}
        return {
            "$or": [
                {"assignment.department_id": user.department_id},
                {"assignment.agent_id": user.id},
            ]
        }
    return {"claimant.user_id": user.id}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

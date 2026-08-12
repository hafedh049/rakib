"""RBAC: role hierarchy, route guards, and the query-level department scope.

The spec is explicit that scoping is enforced by injecting a filter into the query,
never by filtering after fetch — so `department_scope` is tested as a filter.
"""

import pytest
from beanie import PydanticObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import AppError, app_error_handler
from app.deps import department_scope, require_exact_roles, require_role
from app.models.user import Role, role_at_least

DEPT_A = PydanticObjectId()
DEPT_B = PydanticObjectId()


# ------------------------------------------------------------------ role hierarchy
@pytest.mark.parametrize(
    "role,minimum,expected",
    [
        (Role.ADMIN, Role.AGENT, True),
        (Role.SUPERVISOR, Role.AGENT, True),
        (Role.AGENT, Role.AGENT, True),
        (Role.CLAIMANT, Role.AGENT, False),
        (Role.AGENT, Role.SUPERVISOR, False),
        (Role.SUPERVISOR, Role.ADMIN, False),
        (Role.ADMIN, Role.ADMIN, True),
        ("nonsense", Role.CLAIMANT, False),
    ],
)
def test_role_at_least(role, minimum, expected):
    assert role_at_least(role, minimum) is expected


# --------------------------------------------------------------------- route guards
async def _app_with(dependency):
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    from fastapi import Depends

    @app.get("/guarded")
    async def guarded(user=Depends(dependency)):
        return {"role": str(user.role)}

    return app


async def _call(app, headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get("/guarded", headers=headers)


@pytest.mark.parametrize(
    "role,allowed",
    [
        (Role.CLAIMANT, False),
        (Role.AGENT, True),
        (Role.SUPERVISOR, True),
        (Role.ADMIN, True),
    ],
)
async def test_require_role_agent(client, make_user, login, role, allowed):
    await make_user(email=f"{role}@rakib.tn", password="Password123!", role=role)
    headers = await login(client, f"{role}@rakib.tn", "Password123!")

    app = await _app_with(require_role(Role.AGENT))
    response = await _call(app, headers)

    assert (response.status_code == 200) is allowed
    if not allowed:
        assert response.status_code == 403
        assert response.json()["type"] == "/errors/forbidden"


async def test_require_exact_roles_excludes_higher_roles(client, make_user, login):
    """`require_exact_roles` is not a hierarchy — admin is NOT implicitly an agent."""
    await make_user(email="admin@rakib.tn", password="Password123!", role=Role.ADMIN)
    headers = await login(client, "admin@rakib.tn", "Password123!")

    app = await _app_with(require_exact_roles(Role.AGENT))
    assert (await _call(app, headers)).status_code == 403


async def test_guarded_route_rejects_anonymous():
    app = await _app_with(require_role(Role.AGENT))
    assert (await _call(app, {})).status_code == 401


async def test_guarded_route_rejects_garbage_token():
    app = await _app_with(require_role(Role.AGENT))
    response = await _call(app, {"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401
    assert response.json()["type"] == "/errors/token"


# ------------------------------------------------------------------ department scope
def _user(role, department_id=None, user_id=None):
    from app.models.user import User

    user = User(
        email="x@rakib.tn", password_hash="x", full_name="X", role=role,
        department_id=department_id,
    )
    user.id = user_id or PydanticObjectId()
    return user


def test_scope_is_unrestricted_for_supervisor_and_admin():
    assert department_scope(_user(Role.SUPERVISOR)) == {}
    assert department_scope(_user(Role.ADMIN)) == {}


def test_scope_limits_agent_to_own_department_or_own_assignments():
    user = _user(Role.AGENT, department_id=DEPT_A)
    scope = department_scope(user)
    assert scope == {
        "$or": [
            {"assignment.department_id": DEPT_A},
            {"assignment.agent_id": user.id},
        ]
    }
    assert str(DEPT_B) not in str(scope)


def test_scope_for_agent_without_department_is_own_assignments_only():
    user = _user(Role.AGENT)
    assert department_scope(user) == {"assignment.agent_id": user.id}


def test_scope_limits_claimant_to_own_complaints():
    user = _user(Role.CLAIMANT)
    assert department_scope(user) == {"claimant.user_id": user.id}


def test_scope_never_returns_empty_filter_for_non_supervisors():
    """An empty filter means 'read everything' — it must never leak to lower roles."""
    for role in (Role.CLAIMANT, Role.AGENT):
        assert department_scope(_user(role)) != {}

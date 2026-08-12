from datetime import UTC, datetime
from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status
from pydantic import BaseModel, EmailStr, Field

from app.core.errors import Conflict, NotFound, ValidationError
from app.core.security import hash_password
from app.deps import AdminUser, AgentUser, CurrentUser
from app.models.department import Department
from app.models.user import Role, User
from app.schemas.auth import UserOut, normalise_tn_phone

router = APIRouter(prefix="/users", tags=["users"])


class StaffCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    role: Role = Role.AGENT
    department_id: PydanticObjectId | None = None
    skills: list[str] = Field(default_factory=list)
    max_concurrent: int = Field(default=20, ge=1, le=200)
    phone: str | None = None
    locale: str = "fr"


class UserPatch(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    department_id: PydanticObjectId | None = None
    skills: list[str] | None = None
    max_concurrent: int | None = Field(default=None, ge=1, le=200)
    is_active: bool | None = None
    locale: str | None = None
    phone: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.get("", response_model=list[UserOut])
async def list_users(
    _: AgentUser,
    role: Annotated[Role | None, Query()] = None,
    department_id: Annotated[PydanticObjectId | None, Query()] = None,
    active: Annotated[bool | None, Query()] = None,
) -> list[User]:
    query: dict = {}
    if role:
        query["role"] = str(role)
    if department_id:
        query["department_id"] = department_id
    if active is not None:
        query["is_active"] = active
    return await User.find(query).sort(User.full_name).to_list()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_staff(payload: StaffCreate, _: AdminUser) -> User:
    """Staff accounts are created here; claimants self-register via /auth/register."""
    if await User.find_one(User.email == payload.email.lower()):
        raise Conflict("Un compte existe deja avec cet email")
    await _validate_department(payload.department_id)

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        department_id=payload.department_id,
        skills=payload.skills,
        max_concurrent=payload.max_concurrent,
        phone=normalise_tn_phone(payload.phone),
        locale=payload.locale,
    )
    await user.insert()
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def patch_user(
    user_id: PydanticObjectId, payload: UserPatch, admin: AdminUser
) -> User:
    user = await User.get(user_id)
    if user is None:
        raise NotFound("Utilisateur introuvable")

    updates = payload.model_dump(exclude_unset=True)
    if "department_id" in updates:
        await _validate_department(updates["department_id"])
    if updates.get("password"):
        user.password_hash = hash_password(updates.pop("password"))
    else:
        updates.pop("password", None)
    if "phone" in updates:
        updates["phone"] = normalise_tn_phone(updates["phone"])
    if (
        updates.get("is_active") is False or updates.get("role")
    ) and user.id == admin.id:
        raise ValidationError("Impossible de modifier son propre role ou statut")

    for field, value in updates.items():
        setattr(user, field, value)
    user.updated_at = datetime.now(UTC)
    await user.save()
    return user


async def _validate_department(department_id: PydanticObjectId | None) -> None:
    if department_id is None:
        return
    if await Department.get(department_id) is None:
        raise ValidationError("Departement inconnu")

from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import Conflict, NotFound, ValidationError
from app.deps import AdminUser, AgentUser
from app.domain.taxonomy import ALL_CATEGORIES
from app.models.complaint import Complaint
from app.models.department import Department

router = APIRouter(prefix="/departments", tags=["departments"])


class DepartmentIn(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    active: bool = True


class DepartmentPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    keywords: list[str] | None = None
    categories: list[str] | None = None
    active: bool | None = None


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    code: str
    name: str
    description: str
    keywords: list[str]
    categories: list[str]
    active: bool


def _validate_categories(categories: list[str]) -> None:
    unknown = [c for c in categories if c not in ALL_CATEGORIES]
    if unknown:
        raise ValidationError(f"Categories inconnues: {', '.join(unknown)}")


@router.get("", response_model=list[DepartmentOut])
async def list_departments(_: AgentUser) -> list[Department]:
    return await Department.find_all().sort(Department.code).to_list()


@router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(payload: DepartmentIn, _: AdminUser) -> Department:
    if await Department.find_one(Department.code == payload.code):
        raise Conflict(f"Le departement {payload.code} existe deja")
    _validate_categories(payload.categories)
    department = Department(**payload.model_dump())
    await department.insert()
    return department


@router.patch("/{department_id}", response_model=DepartmentOut)
async def patch_department(
    department_id: PydanticObjectId, payload: DepartmentPatch, _: AdminUser
) -> Department:
    department = await Department.get(department_id)
    if department is None:
        raise NotFound("Departement introuvable")
    updates = payload.model_dump(exclude_unset=True)
    if "categories" in updates and updates["categories"] is not None:
        _validate_categories(updates["categories"])
    for field, value in updates.items():
        setattr(department, field, value)
    department.updated_at = datetime.now(UTC)
    await department.save()
    return department


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_department(
    department_id: PydanticObjectId, _: AdminUser
) -> None:
    """Soft delete. Departments are referenced by historical complaints, so they
    are deactivated rather than removed."""
    department = await Department.get(department_id)
    if department is None:
        raise NotFound("Departement introuvable")
    open_count = await Complaint.find(
        {
            "assignment.department_id": department.id,
            "status": {"$nin": ["resolved", "closed", "rejected"]},
        }
    ).count()
    if open_count:
        raise Conflict(
            f"{open_count} reclamation(s) ouverte(s) sur ce departement — "
            "reaffectez-les d'abord"
        )
    department.active = False
    department.updated_at = datetime.now(UTC)
    await department.save()

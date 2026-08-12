from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import Role

# Tunisian mobile/fixed numbers: +216 followed by 8 digits.
TUNISIAN_PHONE_HINT = "+216 XX XXX XXX"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = None
    locale: str = "fr"

    @field_validator("phone")
    @classmethod
    def _normalise_phone(cls, value: str | None) -> str | None:
        return normalise_tn_phone(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    all_sessions: bool = False


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    email: EmailStr
    full_name: str
    role: Role
    department_id: PydanticObjectId | None = None
    skills: list[str] = Field(default_factory=list)
    max_concurrent: int
    is_active: bool
    locale: str
    phone: str | None = None
    last_active_at: datetime | None = None
    created_at: datetime


def normalise_tn_phone(value: str | None) -> str | None:
    """Accept the shapes Tunisians actually type, store one canonical form.

    ``29123456`` / ``29 123 456`` / ``0021629123456`` / ``+216 29 123 456``
    all normalise to ``+21629123456``. Anything else is returned stripped so the
    caller can decide whether to reject it.
    """
    if value is None:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    if not digits:
        return None
    if digits.startswith("00216"):
        digits = digits[5:]
    elif digits.startswith("216") and len(digits) == 11:
        digits = digits[3:]
    if len(digits) == 8:
        return f"+216{digits}"
    return value.strip()


def is_valid_tn_phone(value: str | None) -> bool:
    normalised = normalise_tn_phone(value)
    return bool(
        normalised
        and normalised.startswith("+216")
        and len(normalised) == 12
        and normalised[4:].isdigit()
    )

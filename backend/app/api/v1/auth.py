from fastapi import APIRouter, Request, status

from app.deps import CurrentUser
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> UserOut:
    """Claimant self-signup. Staff accounts are created by an admin, never here."""
    user = await auth_service.register_claimant(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        phone=payload.phone,
        locale=payload.locale,
    )
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, request: Request) -> TokenPair:
    user = await auth_service.authenticate(payload.email, payload.password)
    return await auth_service.issue_token_pair(user, user_agent=_user_agent(request))


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, request: Request) -> TokenPair:
    return await auth_service.rotate_refresh_token(
        payload.refresh_token, user_agent=_user_agent(request)
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, user: CurrentUser) -> None:
    if payload.all_sessions:
        await auth_service.revoke_all_for_user(user.id)
    elif payload.refresh_token:
        await auth_service.revoke_refresh_token(payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)

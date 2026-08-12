"""Registration, login, and refresh-token rotation.

Rotation policy: every successful refresh revokes the presented token and issues a
new one. Presenting an already-revoked token is treated as theft and revokes the
whole family for that user.
"""

from datetime import UTC, datetime

from beanie import PydanticObjectId

from app.core.errors import Conflict, InvalidCredentials, TokenError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    needs_rehash,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import Role, User
from app.schemas.auth import TokenPair

log = get_logger(__name__)


async def register_claimant(
    *,
    email: str,
    password: str,
    full_name: str,
    phone: str | None = None,
    locale: str = "fr",
) -> User:
    if await User.find_one(User.email == email.lower()):
        raise Conflict("Un compte existe deja avec cet email")
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        phone=phone,
        locale=locale,
        role=Role.CLAIMANT,
    )
    await user.insert()
    log.info("auth.registered", user_id=str(user.id), role=user.role)
    return user


async def authenticate(email: str, password: str) -> User:
    user = await User.find_one(User.email == email.lower())
    # Hash a throwaway password when the user is missing so a wrong email and a
    # wrong password take the same time — no user-enumeration oracle here.
    if user is None:
        hash_password(password)
        raise InvalidCredentials()
    if not verify_password(password, user.password_hash):
        raise InvalidCredentials()
    if not user.is_active:
        raise InvalidCredentials("Compte desactive")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_active_at = datetime.now(UTC)
    user.touch()
    await user.save()
    return user


async def issue_token_pair(user: User, user_agent: str | None = None) -> TokenPair:
    access, expires = create_access_token(
        subject=str(user.id),
        role=str(user.role),
        department_id=str(user.department_id) if user.department_id else None,
    )
    raw_refresh, token_hash, refresh_expires = create_refresh_token()
    await RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=refresh_expires,
        user_agent=user_agent,
    ).insert()
    return TokenPair(
        access_token=access, refresh_token=raw_refresh, expires_at=expires
    )


async def rotate_refresh_token(raw_token: str, user_agent: str | None = None) -> TokenPair:
    token_hash = hash_refresh_token(raw_token)
    stored = await RefreshToken.find_one(RefreshToken.token_hash == token_hash)
    if stored is None:
        raise TokenError("Jeton de rafraichissement inconnu")

    if stored.revoked:
        # Replay of a rotated token: assume compromise, drop every session.
        await revoke_all_for_user(stored.user_id)
        log.warning("auth.refresh_replay", user_id=str(stored.user_id))
        raise TokenError("Jeton revoque — toutes les sessions ont ete fermees")

    if stored.expires_at < datetime.now(UTC):
        raise TokenError("Jeton de rafraichissement expire")

    user = await User.get(stored.user_id)
    if user is None or not user.is_active:
        raise TokenError("Compte introuvable ou desactive")

    pair = await issue_token_pair(user, user_agent=user_agent)
    stored.revoked = True
    stored.replaced_by = hash_refresh_token(pair.refresh_token)
    await stored.save()
    return pair


async def revoke_refresh_token(raw_token: str) -> None:
    stored = await RefreshToken.find_one(
        RefreshToken.token_hash == hash_refresh_token(raw_token)
    )
    if stored is not None and not stored.revoked:
        stored.revoked = True
        await stored.save()


async def revoke_all_for_user(user_id: PydanticObjectId | None) -> None:
    if user_id is None:  # unsaved user — nothing to revoke
        return
    await RefreshToken.find(
        RefreshToken.user_id == user_id, RefreshToken.revoked == False  # noqa: E712
    ).set({RefreshToken.revoked: True})

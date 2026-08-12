"""Password hashing, JWT access/refresh, and public tracking tokens.

Three distinct credential kinds, deliberately not interchangeable:
  * access token   — short-lived session bearer (jwt_secret)
  * refresh token  — opaque random string; only its hash is stored (rotation on use)
  * tracking token — signs one public link to ONE complaint (tracking_token_secret).
                     A leaked tracking link must never be usable as a session.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import settings
from app.core.errors import TokenError

_hasher = PasswordHasher()

TokenKind = Literal["access", "refresh"]


# --------------------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False
    return True


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return True


# ------------------------------------------------------------------------- access JWT
def create_access_token(
    subject: str, role: str, department_id: str | None = None
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.jwt_access_ttl_min)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "dept": department_id,
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": secrets.token_hex(8),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Session expiree") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Jeton invalide") from exc
    if payload.get("typ") != "access":
        raise TokenError("Type de jeton incorrect")
    return payload


# ----------------------------------------------------------------------- refresh token
def create_refresh_token() -> tuple[str, str, datetime]:
    """Return (raw_token, token_hash, expires_at). Only the hash is ever persisted."""
    raw = secrets.token_urlsafe(48)
    expires = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_ttl_days)
    return raw, hash_refresh_token(raw), expires


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------- tracking token
def create_tracking_token(complaint_id: str, scope: str = "track") -> str:
    """Sign a public, complaint-scoped link token: <complaint_id>.<scope>.<exp>.<sig>."""
    exp = int(
        (
            datetime.now(UTC) + timedelta(days=settings.tracking_token_ttl_days)
        ).timestamp()
    )
    body = f"{complaint_id}.{scope}.{exp}"
    return f"{body}.{_sign(body)}"


def verify_tracking_token(token: str, scope: str = "track") -> str:
    """Return the complaint_id the token grants access to, or raise TokenError."""
    try:
        complaint_id, token_scope, exp_raw, signature = token.rsplit(".", 3)
    except ValueError as exc:
        raise TokenError("Lien de suivi invalide") from exc

    body = f"{complaint_id}.{token_scope}.{exp_raw}"
    if not hmac.compare_digest(signature, _sign(body)):
        raise TokenError("Lien de suivi invalide")
    if token_scope != scope:
        raise TokenError("Lien de suivi invalide")
    try:
        if int(exp_raw) < datetime.now(UTC).timestamp():
            raise TokenError("Lien de suivi expire")
    except ValueError as exc:
        raise TokenError("Lien de suivi invalide") from exc
    return complaint_id


def _sign(body: str) -> str:
    return hmac.new(
        settings.tracking_token_secret.encode(), body.encode(), hashlib.sha256
    ).hexdigest()

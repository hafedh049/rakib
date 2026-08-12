"""Password hashing, access tokens, and the public tracking-token mechanism.

The tracking token is the control that replaces "track by ref". The spec's original
sequential ref (REC-2026-00412) would have let anyone enumerate every complaint, so
these tests are load-bearing, not incidental.
"""

from datetime import UTC, datetime, timedelta

import pytest
import time_machine

from app.core.errors import TokenError
from app.core.security import (
    create_access_token,
    create_tracking_token,
    decode_access_token,
    hash_password,
    verify_password,
    verify_tracking_token,
)
from app.schemas.auth import is_valid_tn_phone, normalise_tn_phone


# ------------------------------------------------------------------------ passwords
def test_hash_is_salted_so_equal_passwords_differ():
    assert hash_password("Password123!") != hash_password("Password123!")


def test_verify_password_roundtrip():
    digest = hash_password("Password123!")
    assert verify_password("Password123!", digest)
    assert not verify_password("Password123?", digest)


def test_verify_password_survives_a_corrupt_hash():
    assert verify_password("anything", "not-an-argon2-hash") is False


# --------------------------------------------------------------------- access token
def test_access_token_roundtrip():
    token, _ = create_access_token("507f1f77bcf86cd799439011", "agent", None)
    payload = decode_access_token(token)
    assert payload["sub"] == "507f1f77bcf86cd799439011"
    assert payload["role"] == "agent"
    assert payload["typ"] == "access"


def test_expired_access_token_is_rejected():
    token, _ = create_access_token("507f1f77bcf86cd799439011", "agent")
    with time_machine.travel(datetime.now(UTC) + timedelta(hours=2)):
        with pytest.raises(TokenError):
            decode_access_token(token)


def test_tampered_access_token_is_rejected():
    token, _ = create_access_token("507f1f77bcf86cd799439011", "agent")
    head, payload, signature = token.split(".")
    with pytest.raises(TokenError):
        decode_access_token(f"{head}.{payload}.{signature[:-2]}xx")


# ------------------------------------------------------------------- tracking token
def test_tracking_token_roundtrip():
    token = create_tracking_token("507f1f77bcf86cd799439011")
    assert verify_tracking_token(token) == "507f1f77bcf86cd799439011"


def test_tracking_token_is_bound_to_one_complaint():
    """Swapping the id must invalidate the signature — no walking to a neighbour."""
    token = create_tracking_token("507f1f77bcf86cd799439011")
    forged = token.replace("507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012")
    with pytest.raises(TokenError):
        verify_tracking_token(forged)


def test_tracking_token_is_bound_to_its_scope():
    """A 'track' link must not double as a 'satisfaction' link."""
    token = create_tracking_token("507f1f77bcf86cd799439011", scope="track")
    with pytest.raises(TokenError):
        verify_tracking_token(token, scope="satisfaction")


def test_tracking_token_expires():
    token = create_tracking_token("507f1f77bcf86cd799439011")
    with time_machine.travel(datetime.now(UTC) + timedelta(days=400)):
        with pytest.raises(TokenError):
            verify_tracking_token(token)


@pytest.mark.parametrize(
    "garbage", ["", "abc", "a.b.c", "....", "507f1f77bcf86cd799439011.track.999"]
)
def test_malformed_tracking_tokens_are_rejected(garbage):
    with pytest.raises(TokenError):
        verify_tracking_token(garbage)


def test_tracking_token_is_not_a_session_token():
    """It is signed with a different secret and must not decode as an access JWT."""
    token = create_tracking_token("507f1f77bcf86cd799439011")
    with pytest.raises(TokenError):
        decode_access_token(token)


# --------------------------------------------------------------- Tunisian phone form
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("29123456", "+21629123456"),
        ("29 123 456", "+21629123456"),
        ("+216 29 123 456", "+21629123456"),
        ("0021629123456", "+21629123456"),
        ("+21629123456", "+21629123456"),
        (None, None),
    ],
)
def test_normalise_tn_phone(raw, expected):
    assert normalise_tn_phone(raw) == expected


@pytest.mark.parametrize(
    "raw,valid",
    [("29123456", True), ("+21629123456", True), ("123", False), ("+33612345678", False)],
)
def test_is_valid_tn_phone(raw, valid):
    assert is_valid_tn_phone(raw) is valid

import pytest

from app.models.refresh_token import RefreshToken
from app.models.user import Role

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"

VALID = {
    "email": "hedi@example.tn",
    "password": "Password123!",
    "full_name": "Hedi Ben Salah",
    "phone": "29 123 456",
}


async def test_register_creates_claimant_and_normalises_phone(client):
    response = await client.post(REGISTER, json=VALID)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "hedi@example.tn"
    assert body["role"] == Role.CLAIMANT
    # "29 123 456" -> canonical Tunisian form
    assert body["phone"] == "+21629123456"


async def test_register_never_returns_the_password_hash(client):
    response = await client.post(REGISTER, json=VALID)
    assert "password_hash" not in response.json()
    assert "password" not in response.json()


async def test_register_rejects_duplicate_email(client):
    await client.post(REGISTER, json=VALID)
    response = await client.post(REGISTER, json=VALID)
    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_register_rejects_short_password(client):
    response = await client.post(REGISTER, json={**VALID, "password": "short"})
    assert response.status_code == 422
    assert response.json()["type"] == "/errors/validation"


async def test_login_returns_token_pair(client):
    await client.post(REGISTER, json=VALID)
    response = await client.post(
        LOGIN, json={"email": VALID["email"], "password": VALID["password"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


@pytest.mark.parametrize(
    "email,password",
    [
        ("hedi@example.tn", "WrongPassword1!"),
        ("ghost@example.tn", "Password123!"),
    ],
)
async def test_login_failures_are_indistinguishable(client, email, password):
    """Wrong password and unknown account must return the same problem document."""
    await client.post(REGISTER, json=VALID)
    response = await client.post(LOGIN, json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json()["type"] == "/errors/invalid-credentials"


async def test_login_rejects_deactivated_account(client, make_user):
    await make_user(email="off@rakib.tn", password="Password123!", is_active=False)
    response = await client.post(
        LOGIN, json={"email": "off@rakib.tn", "password": "Password123!"}
    )
    assert response.status_code == 401


async def test_me_requires_a_token(client):
    assert (await client.get(ME)).status_code == 401


async def test_me_returns_the_current_user(client, make_user, login):
    await make_user(email="agent@rakib.tn", password="Password123!")
    headers = await login(client, "agent@rakib.tn", "Password123!")
    response = await client.get(ME, headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "agent@rakib.tn"


async def test_refresh_rotates_and_revokes_the_old_token(client):
    await client.post(REGISTER, json=VALID)
    first = (
        await client.post(
            LOGIN, json={"email": VALID["email"], "password": VALID["password"]}
        )
    ).json()

    rotated = await client.post(REFRESH, json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != first["refresh_token"]

    stored = await RefreshToken.find_all().to_list()
    assert sum(1 for t in stored if t.revoked) == 1
    assert sum(1 for t in stored if not t.revoked) == 1


async def test_replaying_a_rotated_token_revokes_every_session(client):
    """A replayed refresh token means the token leaked — drop the whole family."""
    await client.post(REGISTER, json=VALID)
    first = (
        await client.post(
            LOGIN, json={"email": VALID["email"], "password": VALID["password"]}
        )
    ).json()
    await client.post(REFRESH, json={"refresh_token": first["refresh_token"]})

    replay = await client.post(REFRESH, json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401

    stored = await RefreshToken.find_all().to_list()
    assert all(token.revoked for token in stored)


async def test_refresh_rejects_unknown_token(client):
    response = await client.post(REFRESH, json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401


async def test_logout_revokes_the_presented_token(client, login):
    await client.post(REGISTER, json=VALID)
    pair = (
        await client.post(
            LOGIN, json={"email": VALID["email"], "password": VALID["password"]}
        )
    ).json()
    headers = {"Authorization": f"Bearer {pair['access_token']}"}

    assert (
        await client.post(
            LOGOUT, json={"refresh_token": pair["refresh_token"]}, headers=headers
        )
    ).status_code == 204

    replay = await client.post(REFRESH, json={"refresh_token": pair["refresh_token"]})
    assert replay.status_code == 401


async def test_logout_all_sessions(client):
    await client.post(REGISTER, json=VALID)
    creds = {"email": VALID["email"], "password": VALID["password"]}
    one = (await client.post(LOGIN, json=creds)).json()
    two = (await client.post(LOGIN, json=creds)).json()

    headers = {"Authorization": f"Bearer {one['access_token']}"}
    await client.post(LOGOUT, json={"all_sessions": True}, headers=headers)

    for pair in (one, two):
        response = await client.post(
            REFRESH, json={"refresh_token": pair["refresh_token"]}
        )
        assert response.status_code == 401

"""Tests for accounts, sessions and invites."""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.auth import COOKIE_NAME, MAX_FAILED_LOGINS, utcnow
from app.models import Invite
from tests.conftest import ADMIN, FRIEND


def test_should_reject_api_calls_without_session(anon_client: TestClient) -> None:
    assert anon_client.get("/api/workouts").status_code == 401
    assert anon_client.get("/api/auth/me").status_code == 401


def test_should_require_invite_even_with_no_accounts(anon_client: TestClient) -> None:
    response = anon_client.post("/api/auth/signup", json={**ADMIN, "invite_code": "nao-existe"})

    assert response.status_code == 403


def test_should_create_regular_users_from_invites(friend_client: TestClient) -> None:
    assert friend_client.get("/api/auth/me").json()["is_admin"] is False


def test_should_accept_invite_only_once(client: TestClient) -> None:
    code = client.post("/api/invites").json()["code"]

    with TestClient(client.app) as first, TestClient(client.app) as second:
        assert first.post("/api/auth/signup", json={**FRIEND, "invite_code": code}).status_code == 201
        reused = second.post(
            "/api/auth/signup",
            json={**FRIEND, "email": "outro@example.com", "invite_code": code},
        )

    assert reused.status_code == 403
    assert client.get("/api/invites").json()[0]["used_by_name"] == FRIEND["name"]


def test_should_reject_expired_invite(client: TestClient, session_factory: sessionmaker) -> None:
    code = client.post("/api/invites").json()["code"]
    with session_factory() as session:
        session.get(Invite, code).expires_at = utcnow() - timedelta(minutes=1)
        session.commit()

    with TestClient(client.app) as other:
        response = other.post("/api/auth/signup", json={**FRIEND, "invite_code": code})

    assert response.status_code == 403


def test_should_let_only_admin_create_invites(friend_client: TestClient) -> None:
    assert friend_client.post("/api/invites").status_code == 403


def test_should_reject_duplicate_email_ignoring_case(client: TestClient) -> None:
    code = client.post("/api/invites").json()["code"]

    with TestClient(client.app) as other:
        response = other.post(
            "/api/auth/signup",
            json={**FRIEND, "email": ADMIN["email"].upper(), "invite_code": code},
        )

    assert response.status_code == 409


def test_should_reject_short_password(client: TestClient) -> None:
    code = client.post("/api/invites").json()["code"]

    with TestClient(client.app) as other:
        response = other.post("/api/auth/signup", json={**FRIEND, "password": "curta", "invite_code": code})

    assert response.status_code == 422


def test_should_login_and_logout(client: TestClient) -> None:
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    response = client.post("/api/auth/login", json={"email": " Admin@Example.com ", "password": ADMIN["password"]})

    assert response.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_should_invalidate_session_server_side_on_logout(client: TestClient) -> None:
    token = client.cookies.get(COOKIE_NAME)
    client.post("/api/auth/logout")

    client.cookies.set(COOKIE_NAME, token)

    assert client.get("/api/auth/me").status_code == 401


def test_should_reject_wrong_password_and_unknown_email(client: TestClient) -> None:
    client.post("/api/auth/logout")

    wrong = client.post("/api/auth/login", json={"email": ADMIN["email"], "password": "errada-123"})
    unknown = client.post("/api/auth/login", json={"email": "ninguem@example.com", "password": "x"})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_should_throttle_repeated_failed_logins(client: TestClient) -> None:
    client.post("/api/auth/logout")
    for _ in range(MAX_FAILED_LOGINS):
        client.post("/api/auth/login", json={"email": ADMIN["email"], "password": "errada-123"})

    response = client.post("/api/auth/login", json={"email": ADMIN["email"], "password": ADMIN["password"]})

    assert response.status_code == 429


def test_should_store_only_hashed_session_tokens(client: TestClient, session_factory: sessionmaker) -> None:
    from app.models import UserSession

    token = client.cookies.get(COOKIE_NAME)
    with session_factory() as session:
        stored = session.scalars(select(UserSession.token_hash)).all()

    assert token not in stored
    assert len(stored) == 1

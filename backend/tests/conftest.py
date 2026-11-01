"""Shared fixtures: an isolated SQLite database per test and signed-in clients."""

import os
from collections.abc import Iterator

os.environ.setdefault("DATABASE_URL", "sqlite://")
# Set before the app loads backend/.env (which never overrides), so tests ignore a local admin.
os.environ.setdefault("ADMIN_EMAIL", "")
os.environ.setdefault("SECURE_COOKIE", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import login_throttle
from app.db import Base, get_session
from app.main import app
from app.services.admin import ensure_admin

ADMIN = {"name": "Admin", "email": "admin@example.com", "password": "senha-forte-1"}
FRIEND = {"name": "Amigo", "email": "amigo@example.com", "password": "senha-forte-2"}


@pytest.fixture(autouse=True)
def reset_login_throttle() -> Iterator[None]:
    """Failed logins are counted in memory; don't let them leak between tests."""
    login_throttle.clear()
    yield
    login_throttle.clear()


@pytest.fixture
def session_factory() -> Iterator[sessionmaker]:
    """In-memory database shared across connections for one test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def anon_client(session_factory: sessionmaker) -> Iterator[TestClient]:
    """API client wired to the test database, not signed in."""

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session
            session.commit()

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client(anon_client: TestClient, session_factory: sessionmaker) -> TestClient:
    """Client signed in as the admin, created the way production does it (from settings)."""
    with session_factory() as session:
        ensure_admin(session, ADMIN["name"], ADMIN["email"], ADMIN["password"])
        session.commit()
    response = anon_client.post("/api/auth/login", json={"email": ADMIN["email"], "password": ADMIN["password"]})
    assert response.status_code == 200, response.text
    return anon_client


@pytest.fixture
def friend_client(client: TestClient) -> Iterator[TestClient]:
    """A second, separate client signed in as an invited regular user."""
    code = client.post("/api/invites").json()["code"]
    with TestClient(app) as other:
        response = other.post("/api/auth/signup", json={**FRIEND, "invite_code": code})
        assert response.status_code == 201, response.text
        yield other

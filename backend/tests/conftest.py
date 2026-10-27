"""Shared fixtures: an isolated SQLite database per test."""

import os
from collections.abc import Iterator

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("APP_PASSWORD", "")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app


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
def client(session_factory: sessionmaker) -> Iterator[TestClient]:
    """API client wired to the test database."""

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session
            session.commit()

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

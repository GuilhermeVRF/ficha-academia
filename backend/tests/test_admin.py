"""Tests for the admin account managed by environment variables."""

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.auth import password_hasher
from app.models import User, Workout
from app.services.admin import ensure_admin


def test_should_create_admin_and_give_it_ownerless_workouts(session_factory: sessionmaker) -> None:
    with session_factory() as session:
        session.add(Workout(id="legacy", name="Treino antigo", position=0))
        session.flush()

        admin = ensure_admin(session, "Gui", " Gui@Example.com ", "senha-forte-1")
        session.flush()

        assert admin.is_admin
        assert admin.email == "gui@example.com"
        assert session.get(Workout, "legacy").user_id == admin.id


def test_should_be_idempotent(session_factory: sessionmaker) -> None:
    with session_factory() as session:
        ensure_admin(session, "Gui", "gui@example.com", "senha-forte-1")
        ensure_admin(session, "Gui", "gui@example.com", "senha-forte-1")
        session.flush()

        assert len(session.scalars(select(User)).all()) == 1


def test_should_follow_password_and_name_changes_in_environment(session_factory: sessionmaker) -> None:
    with session_factory() as session:
        ensure_admin(session, "Gui", "gui@example.com", "senha-antiga-1")
        admin = ensure_admin(session, "Guilherme", "gui@example.com", "senha-nova-22")

        assert admin.name == "Guilherme"
        assert password_hasher.verify("senha-nova-22", admin.password_hash)
        assert not password_hasher.verify("senha-antiga-1", admin.password_hash)


def test_should_promote_existing_regular_user(session_factory: sessionmaker) -> None:
    with session_factory() as session:
        regular = ensure_admin(session, "Gui", "gui@example.com", "senha-forte-1")
        regular.is_admin = False
        session.flush()

        assert ensure_admin(session, "Gui", "gui@example.com", "senha-forte-1").is_admin

"""End-to-end tests of the HTTP API against an in-memory database."""

from dataclasses import replace
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app import auth
from app.config import Settings
from app.models import Exercise
from app.services.snapshot import record_snapshot

SETS_40 = [{"weight_kg": 40, "reps": 10}] * 3
SETS_45 = [{"weight_kg": 45, "reps": 10}] * 3


@pytest.fixture
def exercise_id(client: TestClient) -> str:
    """Create workout "A" with one exercise and return the exercise id."""
    client.post("/api/workouts", json={"id": "w1", "name": "A"})
    client.post("/api/workouts/w1/exercises", json={"id": "e1", "name": "Supino", "sets": SETS_40})
    return "e1"


def test_should_return_full_tree(client: TestClient, exercise_id: str) -> None:
    tree = client.get("/api/workouts").json()

    assert tree[0]["name"] == "A"
    assert tree[0]["exercises"][0]["sets"] == [{"weight_kg": 40.0, "reps": 10}] * 3


def test_should_ignore_replayed_create_with_same_id(client: TestClient, exercise_id: str) -> None:
    client.post("/api/workouts/w1/exercises", json={"id": "e1", "name": "Outro", "sets": []})

    exercises = client.get("/api/workouts").json()[0]["exercises"]
    assert [exercise["name"] for exercise in exercises] == ["Supino"]


def test_should_collapse_same_day_edits_into_one_snapshot(client: TestClient, exercise_id: str) -> None:
    client.put(f"/api/exercises/{exercise_id}/sets", json={"sets": SETS_45})
    client.put(f"/api/exercises/{exercise_id}/sets", json={"sets": [{"weight_kg": 50, "reps": 8}]})

    history = client.get(f"/api/exercises/{exercise_id}/history").json()

    assert len(history) == 1
    assert history[0]["max_weight_kg"] == 50
    assert history[0]["volume_kg"] == 400


def test_should_drop_todays_snapshot_when_edit_is_reverted(session_factory: sessionmaker) -> None:
    with session_factory() as session:
        exercise = Exercise(id="e1", workout_id="w1", name="Supino")
        session.add(exercise)
        session.flush()
        record_snapshot(session, exercise, today=date(2026, 1, 1))
        record_snapshot(session, exercise, today=date(2026, 1, 2))
        session.flush()

        assert [snapshot.date for snapshot in exercise.snapshots] == [date(2026, 1, 1)]


def test_should_import_text_into_named_and_default_workouts(client: TestClient, exercise_id: str) -> None:
    text = "Crucifixo 3x12 14kg\nTreino B\nAgachamento 4x8 60kg"

    preview = client.post("/api/import-text?dry_run=true", json={"text": text, "workout_id": "w1"}).json()
    assert preview["workouts"][0]["existing_id"] == "w1"
    assert len(client.get("/api/workouts").json()) == 1

    client.post("/api/import-text", json={"text": text, "workout_id": "w1"})
    tree = client.get("/api/workouts").json()
    assert [workout["name"] for workout in tree] == ["A", "Treino B"]
    assert [exercise["name"] for exercise in tree[0]["exercises"]] == ["Supino", "Crucifixo"]


def test_should_round_trip_backup(client: TestClient, exercise_id: str) -> None:
    backup = client.get("/api/export").json()
    client.delete("/api/workouts/w1")

    client.post("/api/import-json", json=backup)

    assert client.get("/api/export").json() == backup


def test_should_reject_requests_without_session_when_password_is_set(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth, "settings", _settings_with_password("segredo"))

    assert client.get("/api/workouts").status_code == 401
    assert client.post("/api/auth/login", json={"password": "segredo"}).status_code == 204
    assert client.get("/api/workouts").status_code == 200


def _settings_with_password(password: str) -> Settings:
    """Copy of the current settings with a password enabled."""
    return replace(auth.settings, app_password=password)

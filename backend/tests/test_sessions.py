"""Tests for workout sessions and workout colors."""

import pytest
from fastapi.testclient import TestClient

SETS = [{"weight_kg": 40, "reps": 10}] * 2


def session_payload(**overrides: object) -> dict:
    """A finished session of workout w1 with one done and one skipped set."""
    payload = {
        "workout_id": "w1",
        "workout_name": "A",
        "started_at": "2026-11-02T07:00:00-03:00",
        "finished_at": "2026-11-02T08:05:00-03:00",
        "sets": [
            {"exercise_id": "e1", "exercise_name": "Supino", "exercise_position": 0, "set_index": 0, "weight_kg": 40, "reps": 10, "done": True},
            {"exercise_id": "e1", "exercise_name": "Supino", "exercise_position": 0, "set_index": 1, "weight_kg": 40, "reps": 8, "done": False},
        ],
    }
    return {**payload, **overrides}


@pytest.fixture
def workout(client: TestClient) -> None:
    """Workout "w1" with exercise "e1"."""
    client.post("/api/workouts", json={"id": "w1", "name": "A"})
    client.post("/api/workouts/w1/exercises", json={"id": "e1", "name": "Supino", "sets": SETS})


@pytest.mark.usefixtures("workout")
def test_should_save_session_and_summarize_it(client: TestClient) -> None:
    saved = client.put("/api/sessions/s1", json=session_payload()).json()

    assert saved["started_at"] == "2026-11-02T10:00:00Z"
    assert saved["workout_color"] == "red"
    assert saved["sets_done"] == 1
    assert saved["volume_kg"] == 400
    assert [item["done"] for item in saved["sets"]] == [True, False]


@pytest.mark.usefixtures("workout")
def test_should_replace_session_when_put_again(client: TestClient) -> None:
    client.put("/api/sessions/s1", json=session_payload())
    client.put("/api/sessions/s1", json=session_payload(notes="ok", sets=[]))

    sessions = client.get("/api/sessions").json()
    assert len(sessions) == 1
    assert sessions[0]["sets_done"] == 0
    assert client.get("/api/sessions/s1").json()["notes"] == "ok"


@pytest.mark.usefixtures("workout")
def test_should_filter_sessions_by_local_day_range(client: TestClient) -> None:
    client.put("/api/sessions/late", json=session_payload(started_at="2026-11-01T23:30:00-03:00", finished_at="2026-11-02T00:30:00-03:00"))
    client.put("/api/sessions/next", json=session_payload())

    in_november_first = client.get(
        "/api/sessions",
        params={"start": "2026-11-01T00:00:00-03:00", "end": "2026-11-02T00:00:00-03:00"},
    ).json()

    assert [item["id"] for item in in_november_first] == ["late"]
    assert [item["id"] for item in client.get("/api/sessions", params={"limit": 1}).json()] == ["next"]


@pytest.mark.usefixtures("workout")
def test_should_reject_session_ending_before_start(client: TestClient) -> None:
    response = client.put("/api/sessions/s1", json=session_payload(finished_at="2026-11-02T06:00:00-03:00"))

    assert response.status_code == 422


@pytest.mark.usefixtures("workout")
def test_should_list_done_sets_of_exercise_by_session(client: TestClient) -> None:
    client.put("/api/sessions/old", json=session_payload(started_at="2026-10-30T07:00:00-03:00", finished_at="2026-10-30T08:00:00-03:00"))
    client.put("/api/sessions/new", json=session_payload())

    points = client.get("/api/exercises/e1/sessions").json()

    assert [point["session_id"] for point in points] == ["new", "old"]
    assert points[0]["sets"] == [{"weight_kg": 40.0, "reps": 10}]


@pytest.mark.usefixtures("workout")
def test_should_keep_sessions_private(client: TestClient, friend_client: TestClient) -> None:
    client.put("/api/sessions/s1", json=session_payload())

    assert friend_client.get("/api/sessions").json() == []
    assert friend_client.get("/api/sessions/s1").status_code == 404
    assert friend_client.put("/api/sessions/s1", json=session_payload()).status_code == 409
    assert friend_client.get("/api/exercises/e1/sessions").status_code == 404
    friend_client.delete("/api/sessions/s1")
    assert client.get("/api/sessions/s1").status_code == 200


@pytest.mark.usefixtures("workout")
def test_should_not_link_session_to_other_users_workout(friend_client: TestClient) -> None:
    saved = friend_client.put("/api/sessions/f1", json=session_payload()).json()

    assert saved["workout_id"] is None
    assert saved["workout_color"] is None
    assert all(item["exercise_id"] is None for item in saved["sets"])


@pytest.mark.usefixtures("workout")
def test_should_delete_session(client: TestClient) -> None:
    client.put("/api/sessions/s1", json=session_payload())

    client.delete("/api/sessions/s1")

    assert client.get("/api/sessions").json() == []


def test_should_give_new_workouts_unused_plate_colors(client: TestClient) -> None:
    for workout_id in ("a", "b", "c"):
        client.post("/api/workouts", json={"id": workout_id, "name": workout_id})
    client.patch("/api/workouts/a", json={"color": "green"})
    client.post("/api/workouts", json={"id": "d", "name": "d"})

    colors = {item["id"]: item["color"] for item in client.get("/api/workouts").json()}
    assert colors == {"a": "green", "b": "blue", "c": "yellow", "d": "red"}


def test_should_reject_unknown_color(client: TestClient) -> None:
    client.post("/api/workouts", json={"id": "a", "name": "a"})

    assert client.patch("/api/workouts/a", json={"color": "pink"}).status_code == 422


@pytest.mark.usefixtures("workout")
def test_should_round_trip_sessions_in_backup(client: TestClient) -> None:
    client.put("/api/sessions/s1", json=session_payload())
    backup = client.get("/api/export").json()

    client.post("/api/import-json", json=backup)

    assert client.get("/api/export").json() == backup
    assert client.get("/api/sessions/s1").json()["workout_id"] == "w1"

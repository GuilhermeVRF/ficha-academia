"""Tests that one account can never read or change another account's data."""

import pytest
from fastapi.testclient import TestClient

SETS = [{"weight_kg": 40, "reps": 10}]


@pytest.fixture
def admin_data(client: TestClient) -> None:
    """Workout "w1" with exercise "e1", owned by the admin."""
    client.post("/api/workouts", json={"id": "w1", "name": "A"})
    client.post("/api/workouts/w1/exercises", json={"id": "e1", "name": "Supino", "sets": SETS})


@pytest.mark.usefixtures("admin_data")
def test_should_list_only_own_workouts(friend_client: TestClient) -> None:
    assert friend_client.get("/api/workouts").json() == []


@pytest.mark.usefixtures("admin_data")
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("PATCH", "/api/workouts/w1", {"name": "Hack"}),
        ("PUT", "/api/workouts/w1/order", {"ids": ["e1"]}),
        ("POST", "/api/workouts/w1/exercises", {"id": "e2", "name": "X", "sets": []}),
        ("PATCH", "/api/exercises/e1", {"name": "Hack"}),
        ("PUT", "/api/exercises/e1/sets", {"sets": SETS}),
        ("GET", "/api/exercises/e1/history", None),
    ],
)
def test_should_hide_other_users_resources(friend_client: TestClient, method: str, path: str, body: dict | None) -> None:
    response = friend_client.request(method, path, json=body)

    assert response.status_code == 404


@pytest.mark.usefixtures("admin_data")
def test_should_not_echo_other_users_data_on_replayed_create(friend_client: TestClient) -> None:
    workout = friend_client.post("/api/workouts", json={"id": "w1", "name": "Meu"})
    exercise = friend_client.post("/api/workouts/w1/exercises", json={"id": "e1", "name": "Meu", "sets": []})

    assert workout.status_code == 409
    assert exercise.status_code in (404, 409)
    assert "Supino" not in workout.text + exercise.text


@pytest.mark.usefixtures("admin_data")
def test_should_ignore_deletes_and_reorders_of_other_users(client: TestClient, friend_client: TestClient) -> None:
    friend_client.post("/api/workouts", json={"id": "fw", "name": "B"})

    friend_client.delete("/api/exercises/e1")
    friend_client.delete("/api/workouts/w1")
    friend_client.put("/api/workouts/order", json={"ids": ["fw", "w1"]})

    tree = client.get("/api/workouts").json()
    assert [workout["id"] for workout in tree] == ["w1"]
    assert tree[0]["position"] == 0
    assert tree[0]["exercises"][0]["id"] == "e1"


@pytest.mark.usefixtures("admin_data")
def test_should_not_move_exercise_into_other_users_workout(friend_client: TestClient) -> None:
    friend_client.post("/api/workouts", json={"id": "fw", "name": "B"})
    friend_client.post("/api/workouts/fw/exercises", json={"id": "fe", "name": "Remada", "sets": []})

    response = friend_client.patch("/api/exercises/fe", json={"workout_id": "w1"})

    assert response.status_code == 404


@pytest.mark.usefixtures("admin_data")
def test_should_export_and_restore_only_own_data(client: TestClient, friend_client: TestClient) -> None:
    friend_client.post("/api/workouts", json={"id": "fw", "name": "B"})
    backup = friend_client.get("/api/export").json()
    assert [workout["id"] for workout in backup["workouts"]] == ["fw"]

    assert friend_client.post("/api/import-json", json=backup).status_code == 204

    assert [workout["id"] for workout in client.get("/api/workouts").json()] == ["w1"]
    assert [workout["id"] for workout in friend_client.get("/api/workouts").json()] == ["fw"]


@pytest.mark.usefixtures("admin_data")
def test_should_refuse_restoring_another_accounts_backup(client: TestClient, friend_client: TestClient) -> None:
    admin_backup = client.get("/api/export").json()

    response = friend_client.post("/api/import-json", json=admin_backup)

    assert response.status_code == 409
    assert client.get("/api/workouts").json()[0]["exercises"][0]["name"] == "Supino"


@pytest.mark.usefixtures("admin_data")
def test_should_import_text_only_into_own_workouts(client: TestClient, friend_client: TestClient) -> None:
    friend_client.post("/api/import-text", json={"text": "Rosca 3x10 12kg", "workout_id": "w1"})
    friend_client.post("/api/import-text", json={"text": "A\nRosca 3x10 12kg"})

    admin_exercises = client.get("/api/workouts").json()[0]["exercises"]
    assert [exercise["name"] for exercise in admin_exercises] == ["Supino"]
    assert len(friend_client.get("/api/workouts").json()) == 2

"""Tests for the exercise library."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models import CatalogExercise
from app.services.catalog import load_library

BENCH = "Barbell_Bench_Press_-_Medium_Grip"


@pytest.fixture(autouse=True)
def library(session_factory: sessionmaker) -> None:
    """Load the real shipped library, as migration 0004 does."""
    with session_factory() as session:
        session.add_all(CatalogExercise(**row) for row in load_library())
        session.commit()


def test_should_ship_a_portuguese_library_with_photos() -> None:
    rows = load_library()

    assert len(rows) > 500
    assert all(row["name_pt"] and row["images"] for row in rows)
    assert len({row["id"] for row in rows}) == len(rows)


def test_should_search_ignoring_accents_case_and_word_order(client: TestClient) -> None:
    names = [item["name"] for item in client.get("/api/catalog", params={"q": "SUPINO barra reto"}).json()]

    assert "Supino reto com barra (pegada média)" in names
    assert all("supino" in name.lower() for name in names)
    assert client.get("/api/catalog", params={"q": "pegada media"}).json()


def test_should_search_english_names_too(client: TestClient) -> None:
    ids = [item["id"] for item in client.get("/api/catalog", params={"q": "bench press"}).json()]

    assert BENCH in ids


def test_should_filter_by_muscle_group(client: TestClient) -> None:
    items = client.get("/api/catalog", params={"group": "panturrilha", "limit": 200}).json()

    assert items
    assert {item["muscle_group"] for item in items} == {"panturrilha"}


def test_should_list_used_exercises_first(client: TestClient) -> None:
    client.post("/api/workouts", json={"id": "w1", "name": "A"})
    client.post("/api/workouts/w1/exercises", json={"id": "e1", "name": "Supino", "sets": [], "catalog_id": BENCH})

    first = client.get("/api/catalog", params={"q": "supino"}).json()[0]

    assert first["id"] == BENCH
    assert first["uses"] == 1


def test_should_return_photos_on_linked_exercises(client: TestClient) -> None:
    client.post("/api/workouts", json={"id": "w1", "name": "A"})
    created = client.post(
        "/api/workouts/w1/exercises",
        json={"id": "e1", "name": "Supino", "sets": [], "catalog_id": BENCH},
    ).json()

    exercise = client.get("/api/workouts").json()[0]["exercises"][0]
    assert created["catalog_id"] == exercise["catalog_id"] == BENCH
    assert len(exercise["images"]) == 2


def test_should_keep_custom_exercises_private(client: TestClient, friend_client: TestClient) -> None:
    created = client.post("/api/catalog", json={"id": "meu-1", "name": "Remada máquina da Smart", "muscle_group": "costas"})

    assert created.status_code == 201
    assert client.get("/api/catalog", params={"q": "smart"}).json()[0]["custom"] is True
    assert friend_client.get("/api/catalog", params={"q": "smart"}).json() == []
    assert friend_client.post("/api/catalog", json={"id": "meu-1", "name": "X"}).status_code == 409


def test_should_not_link_to_other_users_custom_exercise(client: TestClient, friend_client: TestClient) -> None:
    client.post("/api/catalog", json={"id": "meu-1", "name": "Exclusivo"})
    friend_client.post("/api/workouts", json={"id": "fw", "name": "B"})

    exercise = friend_client.post(
        "/api/workouts/fw/exercises",
        json={"id": "fe", "name": "Exclusivo", "sets": [], "catalog_id": "meu-1"},
    ).json()

    assert exercise["catalog_id"] is None


def test_should_round_trip_custom_exercises_and_links_in_backup(client: TestClient) -> None:
    client.post("/api/catalog", json={"id": "meu-1", "name": "Exclusivo", "muscle_group": "pernas"})
    client.post("/api/workouts", json={"id": "w1", "name": "A"})
    client.post("/api/workouts/w1/exercises", json={"id": "e1", "name": "Exclusivo", "sets": [], "catalog_id": "meu-1"})
    client.post("/api/workouts/w1/exercises", json={"id": "e2", "name": "Supino", "sets": [], "catalog_id": BENCH})
    backup = client.get("/api/export").json()

    assert client.post("/api/import-json", json=backup).status_code == 204

    assert client.get("/api/export").json() == backup


def test_should_link_existing_exercise_to_library(client: TestClient) -> None:
    client.post("/api/workouts", json={"id": "w1", "name": "A"})
    client.post("/api/workouts/w1/exercises", json={"id": "e1", "name": "Supino", "sets": []})

    linked = client.patch("/api/exercises/e1", json={"catalog_id": BENCH}).json()
    unlinked = client.patch("/api/exercises/e1", json={"catalog_id": None}).json()

    assert len(linked["images"]) == 2
    assert unlinked["catalog_id"] is None
    assert unlinked["images"] == []

"""Workout and exercise endpoints."""

from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import SessionDep
from app.models import Exercise, ExerciseSet, Workout
from app.schemas import (
    ExerciseCreate,
    ExerciseOut,
    ExerciseUpdate,
    HistoryPoint,
    OrderUpdate,
    SetData,
    SetsReplace,
    WorkoutCreate,
    WorkoutOut,
    WorkoutUpdate,
)
from app.services.snapshot import record_snapshot

router = APIRouter(tags=["workouts"])


@router.get("/workouts", response_model=list[WorkoutOut])
def list_workouts(session: SessionDep) -> list[Workout]:
    """Return the full tree (workouts → exercises → sets) in one request."""
    return list(
        session.scalars(
            select(Workout)
            .options(selectinload(Workout.exercises).selectinload(Exercise.sets))
            .order_by(Workout.position)
        )
    )


@router.post("/workouts", response_model=WorkoutOut, status_code=status.HTTP_201_CREATED)
def create_workout(payload: WorkoutCreate, session: SessionDep) -> Workout:
    """Create a workout at the end of the list; replays with the same id are no-ops."""
    existing = session.get(Workout, payload.id)
    if existing is not None:
        return existing
    next_position = session.scalar(select(func.coalesce(func.max(Workout.position) + 1, 0)))
    workout = Workout(id=payload.id, name=payload.name, position=next_position)
    session.add(workout)
    session.flush()
    return workout


@router.put("/workouts/order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_workouts(payload: OrderUpdate, session: SessionDep) -> None:
    """Reorder workouts by the given id list."""
    for position, workout_id in enumerate(payload.ids):
        workout = session.get(Workout, workout_id)
        if workout is not None:
            workout.position = position


@router.patch("/workouts/{workout_id}", response_model=WorkoutOut)
def update_workout(
    workout_id: str,
    payload: WorkoutUpdate,
    session: SessionDep,
) -> Workout:
    """Rename a workout."""
    workout = _get_workout(session, workout_id)
    if payload.name is not None:
        workout.name = payload.name
    return workout


@router.delete("/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: str, session: SessionDep) -> None:
    """Delete a workout and everything under it; deleting twice is a no-op."""
    workout = session.get(Workout, workout_id)
    if workout is not None:
        session.delete(workout)


@router.put("/workouts/{workout_id}/order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_exercises(
    workout_id: str,
    payload: OrderUpdate,
    session: SessionDep,
) -> None:
    """Reorder the exercises of a workout by the given id list."""
    workout = _get_workout(session, workout_id)
    positions = {exercise_id: index for index, exercise_id in enumerate(payload.ids)}
    for exercise in workout.exercises:
        exercise.position = positions.get(exercise.id, exercise.position)


@router.post(
    "/workouts/{workout_id}/exercises",
    response_model=ExerciseOut,
    status_code=status.HTTP_201_CREATED,
)
def create_exercise(
    workout_id: str,
    payload: ExerciseCreate,
    session: SessionDep,
) -> Exercise:
    """Append an exercise to a workout; replays with the same id are no-ops."""
    existing = session.get(Exercise, payload.id)
    if existing is not None:
        return existing
    workout = _get_workout(session, workout_id)
    exercise = Exercise(
        id=payload.id,
        workout_id=workout.id,
        name=payload.name,
        notes=payload.notes,
        rest_seconds=payload.rest_seconds,
        position=len(workout.exercises),
        sets=_build_sets(payload.sets),
    )
    session.add(exercise)
    session.flush()
    record_snapshot(session, exercise)
    return exercise


@router.patch("/exercises/{exercise_id}", response_model=ExerciseOut)
def update_exercise(
    exercise_id: str,
    payload: ExerciseUpdate,
    session: SessionDep,
) -> Exercise:
    """Update name, notes, rest time or move the exercise to another workout."""
    exercise = _get_exercise(session, exercise_id)
    changes = payload.model_dump(exclude_unset=True)
    if "workout_id" in changes:
        target = _get_workout(session, changes.pop("workout_id"))
        exercise.workout_id = target.id
        exercise.position = len(target.exercises)
    for field_name, value in changes.items():
        setattr(exercise, field_name, value)
    return exercise


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: str, session: SessionDep) -> None:
    """Delete an exercise and its history; deleting twice is a no-op."""
    exercise = session.get(Exercise, exercise_id)
    if exercise is not None:
        session.delete(exercise)


@router.put("/exercises/{exercise_id}/sets", response_model=ExerciseOut)
def replace_sets(
    exercise_id: str,
    payload: SetsReplace,
    session: SessionDep,
) -> Exercise:
    """Replace all sets of an exercise and update today's history snapshot.

    Replacing the whole list keeps the endpoint idempotent, which lets the
    client's offline outbox retry it safely.
    """
    exercise = _get_exercise(session, exercise_id)
    exercise.sets = _build_sets(payload.sets)
    session.flush()
    record_snapshot(session, exercise)
    return exercise


@router.get("/exercises/{exercise_id}/history", response_model=list[HistoryPoint])
def exercise_history(exercise_id: str, session: SessionDep) -> list[HistoryPoint]:
    """Return the daily snapshots of an exercise with summary metrics."""
    exercise = _get_exercise(session, exercise_id)
    return [_to_history_point(snapshot.date, snapshot.sets) for snapshot in exercise.snapshots]


def _get_workout(session: Session, workout_id: str) -> Workout:
    """Load a workout or fail with 404."""
    workout = session.get(Workout, workout_id)
    if workout is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ficha não encontrada")
    return workout


def _get_exercise(session: Session, exercise_id: str) -> Exercise:
    """Load an exercise or fail with 404."""
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercício não encontrado")
    return exercise


def _build_sets(sets: list[SetData]) -> list[ExerciseSet]:
    """Convert payload sets into ORM rows with positions."""
    return [
        ExerciseSet(position=position, weight_kg=item.weight_kg, reps=item.reps)
        for position, item in enumerate(sets)
    ]


def _to_history_point(day: date, raw_sets: list[dict]) -> HistoryPoint:
    """Summarize one snapshot as max weight and total volume."""
    sets = [SetData.model_validate(item) for item in raw_sets]
    return HistoryPoint(
        date=day,
        sets=sets,
        max_weight_kg=max((item.weight_kg for item in sets), default=0),
        volume_kg=sum(item.weight_kg * item.reps for item in sets),
    )

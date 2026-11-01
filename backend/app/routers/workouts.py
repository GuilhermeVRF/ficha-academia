"""Workout and exercise endpoints."""

from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth import CurrentUser
from app.db import SessionDep
from app.models import Exercise, ExerciseSet, User, Workout
from app.schemas import (
    PLATE_COLORS,
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
def list_workouts(user: CurrentUser, session: SessionDep) -> list[Workout]:
    """Return the user's full tree (workouts → exercises → sets) in one request."""
    return list(
        session.scalars(
            select(Workout)
            .where(Workout.user_id == user.id)
            .options(selectinload(Workout.exercises).selectinload(Exercise.sets))
            .order_by(Workout.position)
        )
    )


@router.post("/workouts", response_model=WorkoutOut, status_code=status.HTTP_201_CREATED)
def create_workout(payload: WorkoutCreate, user: CurrentUser, session: SessionDep) -> Workout:
    """Create a workout at the end of the list; replays with the same id are no-ops."""
    existing = session.get(Workout, payload.id)
    if existing is not None:
        _ensure_owner(existing, user)
        return existing
    workout = Workout(
        id=payload.id,
        user_id=user.id,
        name=payload.name,
        position=next_workout_position(session, user),
        color=payload.color or next_workout_color(session, user),
    )
    session.add(workout)
    session.flush()
    return workout


@router.put("/workouts/order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_workouts(payload: OrderUpdate, user: CurrentUser, session: SessionDep) -> None:
    """Reorder the user's workouts by the given id list."""
    for position, workout_id in enumerate(payload.ids):
        workout = session.get(Workout, workout_id)
        if workout is not None and workout.user_id == user.id:
            workout.position = position


@router.patch("/workouts/{workout_id}", response_model=WorkoutOut)
def update_workout(
    workout_id: str,
    payload: WorkoutUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> Workout:
    """Rename a workout or change its color."""
    workout = _get_workout(session, user, workout_id)
    if payload.name is not None:
        workout.name = payload.name
    if payload.color is not None:
        workout.color = payload.color
    return workout


@router.delete("/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: str, user: CurrentUser, session: SessionDep) -> None:
    """Delete a workout and everything under it; deleting twice is a no-op."""
    workout = session.get(Workout, workout_id)
    if workout is not None and workout.user_id == user.id:
        session.delete(workout)


@router.put("/workouts/{workout_id}/order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_exercises(
    workout_id: str,
    payload: OrderUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> None:
    """Reorder the exercises of a workout by the given id list."""
    workout = _get_workout(session, user, workout_id)
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
    user: CurrentUser,
    session: SessionDep,
) -> Exercise:
    """Append an exercise to a workout; replays with the same id are no-ops."""
    existing = session.get(Exercise, payload.id)
    if existing is not None:
        _ensure_owner(existing.workout, user)
        return existing
    workout = _get_workout(session, user, workout_id)
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
    user: CurrentUser,
    session: SessionDep,
) -> Exercise:
    """Update name, notes, rest time or move the exercise to another workout."""
    exercise = _get_exercise(session, user, exercise_id)
    changes = payload.model_dump(exclude_unset=True)
    if "workout_id" in changes:
        target = _get_workout(session, user, changes.pop("workout_id"))
        exercise.workout_id = target.id
        exercise.position = len(target.exercises)
    for field_name, value in changes.items():
        setattr(exercise, field_name, value)
    return exercise


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: str, user: CurrentUser, session: SessionDep) -> None:
    """Delete an exercise and its history; deleting twice is a no-op."""
    exercise = session.get(Exercise, exercise_id)
    if exercise is not None and exercise.workout.user_id == user.id:
        session.delete(exercise)


@router.put("/exercises/{exercise_id}/sets", response_model=ExerciseOut)
def replace_sets(
    exercise_id: str,
    payload: SetsReplace,
    user: CurrentUser,
    session: SessionDep,
) -> Exercise:
    """Replace all sets of an exercise and update today's history snapshot.

    Replacing the whole list keeps the endpoint idempotent, which lets the
    client's offline outbox retry it safely.
    """
    exercise = _get_exercise(session, user, exercise_id)
    exercise.sets = _build_sets(payload.sets)
    session.flush()
    record_snapshot(session, exercise)
    return exercise


@router.get("/exercises/{exercise_id}/history", response_model=list[HistoryPoint])
def exercise_history(exercise_id: str, user: CurrentUser, session: SessionDep) -> list[HistoryPoint]:
    """Return the daily snapshots of an exercise with summary metrics."""
    exercise = _get_exercise(session, user, exercise_id)
    return [_to_history_point(snapshot.date, snapshot.sets) for snapshot in exercise.snapshots]


def next_workout_position(session: Session, user: User) -> int:
    """Position that places a new workout after the user's existing ones."""
    return session.scalar(
        select(func.coalesce(func.max(Workout.position) + 1, 0)).where(Workout.user_id == user.id)
    )


def next_workout_color(session: Session, user: User) -> str:
    """First plate color the user isn't using yet, cycling once all are taken."""
    used = list(session.scalars(select(Workout.color).where(Workout.user_id == user.id)))
    free = [color for color in PLATE_COLORS if color not in used]
    return free[0] if free else PLATE_COLORS[len(used) % len(PLATE_COLORS)]


def _get_workout(session: Session, user: User, workout_id: str) -> Workout:
    """Load one of the user's workouts; other users' workouts look missing (404)."""
    workout = session.get(Workout, workout_id)
    if workout is None or workout.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ficha não encontrada")
    return workout


def _get_exercise(session: Session, user: User, exercise_id: str) -> Exercise:
    """Load one of the user's exercises; other users' exercises look missing (404)."""
    exercise = session.get(Exercise, exercise_id)
    if exercise is None or exercise.workout.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercício não encontrado")
    return exercise


def _ensure_owner(workout: Workout, user: User) -> None:
    """Reject a replayed create whose client id already belongs to another account.

    Raises:
        HTTPException: 409, so the id is never echoed back with someone else's data.
    """
    if workout.user_id != user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Identificador já em uso")


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

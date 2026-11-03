"""JSON backup: export and restore all of a user's data."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth import CurrentUser
from app.db import SessionDep
from app.models import (
    CatalogExercise,
    Exercise,
    ExerciseSet,
    ExerciseSnapshot,
    SessionSet,
    User,
    Workout,
    WorkoutSession,
)
from app.routers.catalog import visible_catalog_id
from app.routers.sessions import to_naive_utc
from app.schemas import Backup, CatalogCreate, SessionBackup, WorkoutBackup
from app.services.catalog import search_key

router = APIRouter(tags=["backup"])


@router.get("/export", response_model=Backup)
def export_backup(user: CurrentUser, session: SessionDep) -> Backup:
    """Dump the user's workouts, exercises, sets, history, sessions and custom exercises."""
    workouts = session.scalars(
        select(Workout)
        .where(Workout.user_id == user.id)
        .options(
            selectinload(Workout.exercises).selectinload(Exercise.sets),
            selectinload(Workout.exercises).selectinload(Exercise.snapshots),
            selectinload(Workout.exercises).selectinload(Exercise.catalog),
        )
        .order_by(Workout.position)
    )
    sessions = session.scalars(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user.id)
        .options(selectinload(WorkoutSession.sets))
        .order_by(WorkoutSession.started_at)
    )
    custom = [
        CatalogCreate(id=item.id, name=item.name_pt, muscle_group=item.muscle_group, equipment=item.equipment)
        for item in session.scalars(
            select(CatalogExercise).where(CatalogExercise.user_id == user.id).order_by(CatalogExercise.name_pt)
        )
    ]
    backup = Backup.model_validate({"workouts": list(workouts), "sessions": list(sessions)}, from_attributes=True)
    backup.custom_exercises = custom
    return backup


@router.post("/import-json", status_code=status.HTTP_204_NO_CONTENT)
def import_backup(backup: Backup, user: CurrentUser, session: SessionDep) -> None:
    """Replace all of the user's data with the contents of a backup file.

    Raises:
        HTTPException: 400 for an unknown version, 409 when the file holds ids
            that belong to another account (e.g. someone else's backup).
    """
    if backup.version != 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Versão de backup não suportada")
    for model in (WorkoutSession, Workout, CatalogExercise):
        for row in session.scalars(select(model).where(model.user_id == user.id)):
            session.delete(row)
    session.flush()
    if _ids_taken(session, backup):
        raise HTTPException(status.HTTP_409_CONFLICT, "Este backup pertence a outra conta.")
    for custom in backup.custom_exercises:
        session.add(_custom_from_backup(custom, user))
    session.flush()
    for workout_data in backup.workouts:
        session.add(_workout_from_backup(session, workout_data, user))
    session.flush()
    restored_exercises = {exercise.id for workout in backup.workouts for exercise in workout.exercises}
    restored_workouts = {workout.id for workout in backup.workouts}
    for session_data in backup.sessions:
        session.add(_session_from_backup(session_data, user, restored_workouts, restored_exercises))


def _ids_taken(session: Session, backup: Backup) -> bool:
    """Whether any id in the backup still exists (after the user's own data was removed)."""
    workout_ids = [workout.id for workout in backup.workouts]
    exercise_ids = [exercise.id for workout in backup.workouts for exercise in workout.exercises]
    session_ids = [item.id for item in backup.sessions]
    custom_ids = [item.id for item in backup.custom_exercises]
    return any(
        session.scalar(select(func.count()).select_from(model).where(model.id.in_(ids)))
        for model, ids in (
            (Workout, workout_ids),
            (Exercise, exercise_ids),
            (WorkoutSession, session_ids),
            (CatalogExercise, custom_ids),
        )
    )


def _custom_from_backup(data: CatalogCreate, user: User) -> CatalogExercise:
    """Rebuild one of the user's own catalog exercises."""
    return CatalogExercise(
        id=data.id,
        user_id=user.id,
        name_pt=data.name,
        name_en="",
        muscle_group=data.muscle_group,
        equipment=data.equipment,
        images=[],
        search_text=search_key(data.name),
    )


def _workout_from_backup(session: Session, data: WorkoutBackup, user: User) -> Workout:
    """Rebuild an ORM workout tree; library links survive only if the entry still exists."""
    return Workout(
        id=data.id,
        user_id=user.id,
        name=data.name,
        position=data.position,
        color=data.color,
        exercises=[
            Exercise(
                id=exercise.id,
                name=exercise.name,
                position=exercise.position,
                notes=exercise.notes,
                rest_seconds=exercise.rest_seconds,
                catalog_id=visible_catalog_id(session, user, exercise.catalog_id),
                sets=[
                    ExerciseSet(position=index, weight_kg=item.weight_kg, reps=item.reps)
                    for index, item in enumerate(exercise.sets)
                ],
                snapshots=[
                    ExerciseSnapshot(date=snapshot.date, sets=[item.model_dump() for item in snapshot.sets])
                    for snapshot in exercise.snapshots
                ],
            )
            for exercise in data.exercises
        ],
    )


def _session_from_backup(
    data: SessionBackup,
    user: User,
    workout_ids: set[str],
    exercise_ids: set[str],
) -> WorkoutSession:
    """Rebuild a session, keeping links only to workouts and exercises restored with it."""
    return WorkoutSession(
        id=data.id,
        user_id=user.id,
        workout_id=data.workout_id if data.workout_id in workout_ids else None,
        workout_name=data.workout_name,
        started_at=to_naive_utc(data.started_at),
        finished_at=to_naive_utc(data.finished_at),
        notes=data.notes,
        sets=[
            SessionSet(
                **item.model_dump(exclude={"exercise_id"}),
                exercise_id=item.exercise_id if item.exercise_id in exercise_ids else None,
            )
            for item in data.sets
        ],
    )

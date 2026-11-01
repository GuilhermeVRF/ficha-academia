"""Bulk text import and JSON backup endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth import CurrentUser
from app.db import SessionDep
from app.models import Exercise, ExerciseSet, ExerciseSnapshot, User, Workout
from app.routers.workouts import next_workout_position
from app.schemas import (
    Backup,
    ImportedExercise,
    ImportedWorkout,
    ImportPreview,
    ImportTextRequest,
    SetData,
    WorkoutBackup,
)
from app.services.snapshot import record_snapshot
from app.services.text_parser import ParsedWorkout, parse_routine

router = APIRouter(tags=["import"])

UNNAMED_WORKOUT = "Treino"


@router.post("/import-text", response_model=ImportPreview)
def import_text(
    payload: ImportTextRequest,
    user: CurrentUser,
    session: SessionDep,
    dry_run: bool = Query(default=False),
) -> ImportPreview:
    """Parse a pasted routine and, unless ``dry_run``, append it to the database.

    Lines before any header go to ``workout_id`` when given; named blocks are
    matched to existing workouts by name (case-insensitive) or created.
    """
    blocks = parse_routine(payload.text)
    preview = ImportPreview(workouts=[_preview_block(session, user, block, payload.workout_id) for block in blocks])
    if not dry_run:
        _apply_preview(session, user, preview)
    return preview


def _preview_block(
    session: Session,
    user: User,
    block: ParsedWorkout,
    default_workout_id: str | None,
) -> ImportedWorkout:
    """Resolve which of the user's workouts a parsed block maps to and convert its exercises."""
    existing = _resolve_workout(session, user, block.name, default_workout_id)
    name = existing.name if existing is not None else block.name or UNNAMED_WORKOUT
    return ImportedWorkout(
        name=name,
        existing_id=existing.id if existing is not None else None,
        exercises=[
            ImportedExercise(
                name=exercise.name,
                sets=[SetData(weight_kg=weight, reps=reps) for weight, reps in exercise.sets],
                warning=exercise.warning,
            )
            for exercise in block.exercises
        ],
    )


def _resolve_workout(
    session: Session,
    user: User,
    name: str | None,
    default_workout_id: str | None,
) -> Workout | None:
    """Find the user's target workout for a block, by name or by the default id."""
    if name is None:
        workout = session.get(Workout, default_workout_id) if default_workout_id else None
        return workout if workout is not None and workout.user_id == user.id else None
    return session.scalar(
        select(Workout).where(Workout.user_id == user.id, func.lower(Workout.name) == name.lower())
    )


def _apply_preview(session: Session, user: User, preview: ImportPreview) -> None:
    """Create the workouts and exercises described by a preview."""
    for block in preview.workouts:
        workout = _get_or_create_workout(session, user, block)
        start = len(workout.exercises)
        for offset, item in enumerate(block.exercises):
            exercise = Exercise(
                id=str(uuid.uuid4()),
                workout_id=workout.id,
                name=item.name,
                position=start + offset,
                sets=[
                    ExerciseSet(position=index, weight_kg=set_data.weight_kg, reps=set_data.reps)
                    for index, set_data in enumerate(item.sets)
                ],
            )
            session.add(exercise)
            session.flush()
            record_snapshot(session, exercise)
        block.existing_id = workout.id


def _get_or_create_workout(session: Session, user: User, block: ImportedWorkout) -> Workout:
    """Return the block's existing workout (already resolved within the user's) or append a new one."""
    if block.existing_id is not None:
        return session.get(Workout, block.existing_id)
    workout = Workout(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=block.name,
        position=next_workout_position(session, user),
    )
    session.add(workout)
    session.flush()
    return workout


@router.get("/export", response_model=Backup)
def export_backup(user: CurrentUser, session: SessionDep) -> Backup:
    """Dump the user's workouts, exercises, sets and history."""
    workouts = session.scalars(
        select(Workout)
        .where(Workout.user_id == user.id)
        .options(
            selectinload(Workout.exercises).selectinload(Exercise.sets),
            selectinload(Workout.exercises).selectinload(Exercise.snapshots),
        )
        .order_by(Workout.position)
    )
    return Backup.model_validate({"workouts": list(workouts)}, from_attributes=True)


@router.post("/import-json", status_code=status.HTTP_204_NO_CONTENT)
def import_backup(backup: Backup, user: CurrentUser, session: SessionDep) -> None:
    """Replace all of the user's data with the contents of a backup file.

    Raises:
        HTTPException: 400 for an unknown version, 409 when the file holds ids
            that belong to another account (e.g. someone else's backup).
    """
    if backup.version != 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Versão de backup não suportada")
    for workout in session.scalars(select(Workout).where(Workout.user_id == user.id)):
        session.delete(workout)
    session.flush()
    if _ids_taken(session, backup):
        raise HTTPException(status.HTTP_409_CONFLICT, "Este backup pertence a outra conta.")
    for workout_data in backup.workouts:
        session.add(_workout_from_backup(workout_data, user))


def _ids_taken(session: Session, backup: Backup) -> bool:
    """Whether any workout or exercise id in the backup still exists (after the user's own were removed)."""
    workout_ids = [workout.id for workout in backup.workouts]
    exercise_ids = [exercise.id for workout in backup.workouts for exercise in workout.exercises]
    taken_workouts = session.scalar(select(func.count()).select_from(Workout).where(Workout.id.in_(workout_ids)))
    taken_exercises = session.scalar(select(func.count()).select_from(Exercise).where(Exercise.id.in_(exercise_ids)))
    return bool(taken_workouts or taken_exercises)


def _workout_from_backup(data: WorkoutBackup, user: User) -> Workout:
    """Rebuild an ORM workout tree from its backup representation."""
    return Workout(
        id=data.id,
        user_id=user.id,
        name=data.name,
        position=data.position,
        exercises=[
            Exercise(
                id=exercise.id,
                name=exercise.name,
                position=exercise.position,
                notes=exercise.notes,
                rest_seconds=exercise.rest_seconds,
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

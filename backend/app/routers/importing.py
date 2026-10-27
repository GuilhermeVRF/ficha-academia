"""Bulk text import and JSON backup endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.db import SessionDep
from app.models import Exercise, ExerciseSet, ExerciseSnapshot, Workout
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
    session: SessionDep,
    dry_run: bool = Query(default=False),
) -> ImportPreview:
    """Parse a pasted routine and, unless ``dry_run``, append it to the database.

    Lines before any header go to ``workout_id`` when given; named blocks are
    matched to existing workouts by name (case-insensitive) or created.
    """
    blocks = parse_routine(payload.text)
    preview = ImportPreview(workouts=[_preview_block(session, block, payload.workout_id) for block in blocks])
    if not dry_run:
        _apply_preview(session, preview)
    return preview


def _preview_block(session: Session, block: ParsedWorkout, default_workout_id: str | None) -> ImportedWorkout:
    """Resolve which workout a parsed block maps to and convert its exercises."""
    existing = _resolve_workout(session, block.name, default_workout_id)
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


def _resolve_workout(session: Session, name: str | None, default_workout_id: str | None) -> Workout | None:
    """Find the target workout for a block, by name or by the default id."""
    if name is None:
        return session.get(Workout, default_workout_id) if default_workout_id else None
    return session.scalar(select(Workout).where(func.lower(Workout.name) == name.lower()))


def _apply_preview(session: Session, preview: ImportPreview) -> None:
    """Create the workouts and exercises described by a preview."""
    for block in preview.workouts:
        workout = _get_or_create_workout(session, block)
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


def _get_or_create_workout(session: Session, block: ImportedWorkout) -> Workout:
    """Return the block's existing workout or append a new one."""
    if block.existing_id is not None:
        return session.get(Workout, block.existing_id)
    next_position = session.scalar(select(func.coalesce(func.max(Workout.position) + 1, 0)))
    workout = Workout(id=str(uuid.uuid4()), name=block.name, position=next_position)
    session.add(workout)
    session.flush()
    return workout


@router.get("/export", response_model=Backup)
def export_backup(session: SessionDep) -> Backup:
    """Dump all workouts, exercises, sets and history."""
    workouts = session.scalars(
        select(Workout)
        .options(
            selectinload(Workout.exercises).selectinload(Exercise.sets),
            selectinload(Workout.exercises).selectinload(Exercise.snapshots),
        )
        .order_by(Workout.position)
    )
    return Backup.model_validate({"workouts": list(workouts)}, from_attributes=True)


@router.post("/import-json", status_code=status.HTTP_204_NO_CONTENT)
def import_backup(backup: Backup, session: SessionDep) -> None:
    """Replace ALL data with the contents of a backup file."""
    if backup.version != 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Versão de backup não suportada")
    for model in (ExerciseSnapshot, ExerciseSet, Exercise, Workout):
        session.execute(delete(model))
    for workout_data in backup.workouts:
        session.add(_workout_from_backup(workout_data))


def _workout_from_backup(data: WorkoutBackup) -> Workout:
    """Rebuild an ORM workout tree from its backup representation."""
    return Workout(
        id=data.id,
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

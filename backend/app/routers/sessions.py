"""Workout sessions: what was actually trained, and when."""

from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import CurrentUser
from app.db import SessionDep
from app.models import Exercise, SessionSet, User, Workout, WorkoutSession
from app.schemas import (
    ExerciseSessionPoint,
    SessionIn,
    SessionOut,
    SessionSetData,
    SessionSummary,
    SetData,
)

MAX_SESSIONS_PER_REQUEST = 500
DEFAULT_EXERCISE_SESSIONS = 10

router = APIRouter(tags=["sessions"])

SessionId = Annotated[str, Path(min_length=1, max_length=36)]


@router.put("/sessions/{session_id}", response_model=SessionOut)
def save_session(session_id: SessionId, payload: SessionIn, user: CurrentUser, session: SessionDep) -> SessionOut:
    """Create or replace a finished session; the client-made id keeps outbox retries idempotent.

    Raises:
        HTTPException: 409 when the id belongs to another account, 422 when it ends before it starts.
    """
    if payload.finished_at < payload.started_at:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "O treino termina antes de começar")
    workout_session = session.get(WorkoutSession, session_id)
    if workout_session is not None and workout_session.user_id != user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Identificador já em uso")
    # A workout or exercise deleted on another device before this synced just loses the link.
    own_exercises = _own_exercise_ids(session, user, {item.exercise_id for item in payload.sets if item.exercise_id})
    workout_id = payload.workout_id if _owns_workout(session, user, payload.workout_id) else None
    if workout_session is None:
        workout_session = WorkoutSession(id=session_id, user_id=user.id)
        session.add(workout_session)
    workout_session.workout_id = workout_id
    workout_session.workout_name = payload.workout_name
    workout_session.started_at = to_naive_utc(payload.started_at)
    workout_session.finished_at = to_naive_utc(payload.finished_at)
    workout_session.notes = payload.notes
    workout_session.sets = [
        SessionSet(**item.model_dump(exclude={"exercise_id"}), exercise_id=item.exercise_id if item.exercise_id in own_exercises else None)
        for item in payload.sets
    ]
    session.flush()
    session.refresh(workout_session, ["workout"])
    return _to_out(workout_session)


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions(
    user: CurrentUser,
    session: SessionDep,
    start: Annotated[datetime | None, Query(description="Inclusive, with timezone offset")] = None,
    end: Annotated[datetime | None, Query(description="Exclusive, with timezone offset")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_SESSIONS_PER_REQUEST)] = MAX_SESSIONS_PER_REQUEST,
) -> list[SessionSummary]:
    """List the user's sessions, newest first, optionally within [start, end)."""
    query = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user.id)
        .options(selectinload(WorkoutSession.sets), selectinload(WorkoutSession.workout))
        .order_by(WorkoutSession.started_at.desc())
        .limit(limit)
    )
    if start is not None:
        query = query.where(WorkoutSession.started_at >= to_naive_utc(start))
    if end is not None:
        query = query.where(WorkoutSession.started_at < to_naive_utc(end))
    return [_to_summary(item) for item in session.scalars(query)]


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: SessionId, user: CurrentUser, session: SessionDep) -> SessionOut:
    """Return one of the user's sessions with all its sets."""
    workout_session = session.get(WorkoutSession, session_id)
    if workout_session is None or workout_session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treino não encontrado")
    return _to_out(workout_session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: SessionId, user: CurrentUser, session: SessionDep) -> None:
    """Delete a session; deleting twice (or someone else's) is a no-op."""
    workout_session = session.get(WorkoutSession, session_id)
    if workout_session is not None and workout_session.user_id == user.id:
        session.delete(workout_session)


@router.get("/exercises/{exercise_id}/sessions", response_model=list[ExerciseSessionPoint])
def exercise_sessions(
    exercise_id: str,
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = DEFAULT_EXERCISE_SESSIONS,
) -> list[ExerciseSessionPoint]:
    """The sets actually done for an exercise in its latest sessions, newest first."""
    exercise = session.get(Exercise, exercise_id)
    if exercise is None or exercise.workout.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercício não encontrado")
    session_ids = session.scalars(
        select(WorkoutSession.id)
        .join(SessionSet)
        .where(WorkoutSession.user_id == user.id, SessionSet.exercise_id == exercise_id, SessionSet.done)
        .group_by(WorkoutSession.id, WorkoutSession.started_at)
        .order_by(WorkoutSession.started_at.desc())
        .limit(limit)
    ).all()
    rows = session.execute(
        select(WorkoutSession.id, WorkoutSession.started_at, SessionSet)
        .join(SessionSet)
        .where(WorkoutSession.id.in_(session_ids), SessionSet.exercise_id == exercise_id, SessionSet.done)
        .order_by(WorkoutSession.started_at.desc(), SessionSet.set_index)
    ).all()
    grouped: defaultdict[str, list[SetData]] = defaultdict(list)
    started: dict[str, datetime] = {}
    for workout_session_id, started_at, item in rows:
        started[workout_session_id] = started_at
        grouped[workout_session_id].append(SetData(weight_kg=item.weight_kg, reps=item.reps))
    return [
        ExerciseSessionPoint(session_id=key, started_at=started[key], sets=sets) for key, sets in grouped.items()
    ]


def to_naive_utc(value: datetime) -> datetime:
    """Convert to the naive-UTC form stored in the database (naive input is taken as UTC)."""
    return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value


def _owns_workout(session: Session, user: User, workout_id: str | None) -> bool:
    """Whether ``workout_id`` is one of the user's workouts."""
    workout = session.get(Workout, workout_id) if workout_id else None
    return workout is not None and workout.user_id == user.id


def _own_exercise_ids(session: Session, user: User, exercise_ids: set[str]) -> set[str]:
    """The subset of ``exercise_ids`` that belong to the user."""
    if not exercise_ids:
        return set()
    return set(
        session.scalars(
            select(Exercise.id).join(Workout).where(Exercise.id.in_(exercise_ids), Workout.user_id == user.id)
        )
    )


def _to_summary(workout_session: WorkoutSession) -> SessionSummary:
    """Summarize a session for the calendar."""
    done = [item for item in workout_session.sets if item.done]
    return SessionSummary(
        id=workout_session.id,
        workout_id=workout_session.workout_id,
        workout_name=workout_session.workout_name,
        workout_color=workout_session.workout.color if workout_session.workout else None,
        started_at=workout_session.started_at,
        finished_at=workout_session.finished_at,
        sets_done=len(done),
        volume_kg=sum(item.weight_kg * item.reps for item in done),
    )


def _to_out(workout_session: WorkoutSession) -> SessionOut:
    """A session with all its sets."""
    return SessionOut(
        **_to_summary(workout_session).model_dump(),
        notes=workout_session.notes,
        sets=[SessionSetData.model_validate(item) for item in workout_session.sets],
    )

"""Daily history snapshots derived from edits to an exercise's sets."""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Exercise, ExerciseSnapshot


def record_snapshot(session: Session, exercise: Exercise, today: date | None = None) -> None:
    """Store the exercise's current sets as the snapshot for today.

    Several edits on the same day collapse into a single snapshot. If the
    result matches the previous day's snapshot (e.g. an edit was reverted),
    today's snapshot is dropped so the chart doesn't get a flat duplicate point.

    Args:
        session: Active database session.
        exercise: Exercise whose sets were just changed (already flushed).
        today: Day to record under; defaults to the current day in the app timezone.
    """
    today = today or local_today()
    current_sets = serialize_sets(exercise)
    todays = _find_snapshot(session, exercise.id, today)
    previous = _previous_snapshot(session, exercise.id, today)

    if previous is not None and previous.sets == current_sets:
        if todays is not None:
            session.delete(todays)
        return
    if todays is None:
        session.add(ExerciseSnapshot(exercise_id=exercise.id, date=today, sets=current_sets))
    else:
        todays.sets = current_sets


def local_today() -> date:
    """Current calendar day in the configured timezone."""
    return datetime.now(settings.timezone).date()


def serialize_sets(exercise: Exercise) -> list[dict]:
    """Convert ORM sets into the JSON shape stored in snapshots."""
    return [{"weight_kg": item.weight_kg, "reps": item.reps} for item in exercise.sets]


def _find_snapshot(session: Session, exercise_id: str, day: date) -> ExerciseSnapshot | None:
    """Fetch the snapshot of one exact day."""
    return session.scalar(
        select(ExerciseSnapshot).where(
            ExerciseSnapshot.exercise_id == exercise_id,
            ExerciseSnapshot.date == day,
        )
    )


def _previous_snapshot(session: Session, exercise_id: str, day: date) -> ExerciseSnapshot | None:
    """Fetch the latest snapshot strictly before ``day``."""
    return session.scalar(
        select(ExerciseSnapshot)
        .where(
            ExerciseSnapshot.exercise_id == exercise_id,
            ExerciseSnapshot.date < day,
        )
        .order_by(ExerciseSnapshot.date.desc())
        .limit(1)
    )

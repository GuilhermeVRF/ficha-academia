"""ORM models.

Primary keys are client-generated UUID strings so the PWA can create
records while offline and replay them idempotently later.
"""

from datetime import date

from sqlalchemy import JSON, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Workout(Base):
    """A routine division (e.g. "Treino A")."""

    __tablename__ = "workout"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    position: Mapped[int] = mapped_column(Integer, default=0)

    exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="Exercise.position",
    )


class Exercise(Base):
    """An exercise inside a workout, holding its current prescribed sets."""

    __tablename__ = "exercise"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workout_id: Mapped[str] = mapped_column(ForeignKey("workout.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    workout: Mapped[Workout] = relationship(back_populates="exercises")
    sets: Mapped[list["ExerciseSet"]] = relationship(
        cascade="all, delete-orphan",
        order_by="ExerciseSet.position",
    )
    snapshots: Mapped[list["ExerciseSnapshot"]] = relationship(
        cascade="all, delete-orphan",
        order_by="ExerciseSnapshot.date",
    )


class ExerciseSet(Base):
    """One set of an exercise's current prescription."""

    __tablename__ = "exercise_set"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    weight_kg: Mapped[float] = mapped_column(Float, default=0)
    reps: Mapped[int] = mapped_column(Integer, default=0)


class ExerciseSnapshot(Base):
    """The state of an exercise's sets at the end of a given day."""

    __tablename__ = "exercise_snapshot"
    __table_args__ = (UniqueConstraint("exercise_id", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date)
    sets: Mapped[list[dict]] = mapped_column(JSON)

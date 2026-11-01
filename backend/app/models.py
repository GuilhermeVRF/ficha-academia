"""ORM models.

Primary keys are client-generated UUID strings so the PWA can create
records while offline and replay them idempotently later.
"""

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    """An account; every workout belongs to exactly one user."""

    __tablename__ = "app_user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class UserSession(Base):
    """A login on one device, looked up by the SHA-256 of the cookie token."""

    __tablename__ = "user_session"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship()


class Invite(Base):
    """A single-use signup code created by an admin."""

    __tablename__ = "invite"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"))
    used_by_id: Mapped[str | None] = mapped_column(ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    used_by: Mapped[User | None] = relationship(foreign_keys=[used_by_id])


class Workout(Base):
    """A routine division (e.g. "Treino A")."""

    __tablename__ = "workout"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Nullable only so data created before accounts existed survives until the first signup claims it.
    user_id: Mapped[str | None] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True, nullable=True)
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

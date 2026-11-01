"""Request and response models for the API."""

from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, PlainSerializer

PlateColor = Literal["red", "blue", "yellow", "green", "white"]
PLATE_COLORS: tuple[PlateColor, ...] = ("red", "blue", "yellow", "green", "white")

# The database stores naive UTC; always send it with an explicit offset so clients show local time.
UtcDatetime = Annotated[
    datetime,
    PlainSerializer(lambda value: value if value.tzinfo else value.replace(tzinfo=UTC), return_type=datetime),
]


class SetData(BaseModel):
    """One set as exchanged with the client."""

    model_config = ConfigDict(from_attributes=True)

    weight_kg: float = Field(ge=0, le=2000)
    reps: int = Field(ge=0, le=1000)


class ExerciseOut(BaseModel):
    """An exercise with its current sets."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    position: int
    notes: str
    rest_seconds: int | None
    sets: list[SetData]


class WorkoutOut(BaseModel):
    """A workout with all its exercises."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    position: int
    color: PlateColor
    exercises: list[ExerciseOut]


class WorkoutCreate(BaseModel):
    """Payload to create a workout; the id comes from the client."""

    id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=120)
    color: PlateColor | None = None


class WorkoutUpdate(BaseModel):
    """Partial update of a workout."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    color: PlateColor | None = None


class ExerciseCreate(BaseModel):
    """Payload to create an exercise; the id comes from the client."""

    id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=200)
    sets: list[SetData] = Field(max_length=50)
    notes: str = ""
    rest_seconds: int | None = None


class ExerciseUpdate(BaseModel):
    """Partial update of an exercise's metadata (sets have their own endpoint)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    rest_seconds: int | None = None
    workout_id: str | None = None


class SetsReplace(BaseModel):
    """Full replacement of an exercise's sets."""

    sets: list[SetData] = Field(max_length=50)


class OrderUpdate(BaseModel):
    """New ordering expressed as the full list of ids."""

    ids: list[str]


class HistoryPoint(BaseModel):
    """One day in an exercise's history."""

    date: date
    sets: list[SetData]
    max_weight_kg: float
    volume_kg: float


MIN_PASSWORD_LENGTH = 8


class LoginRequest(BaseModel):
    """Email and password login."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(max_length=200)


class SignupRequest(BaseModel):
    """New account created from an invite."""

    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)
    invite_code: str = Field(min_length=1, max_length=32)


class UserOut(BaseModel):
    """The signed-in user as shown to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    is_admin: bool


class InviteOut(BaseModel):
    """An invite and whether someone already used it."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    created_at: datetime
    expires_at: datetime
    used_by_name: str | None = None


class ImportTextRequest(BaseModel):
    """Bulk text import payload."""

    text: str = Field(max_length=20000)
    workout_id: str | None = None


class ImportedExercise(BaseModel):
    """An exercise recognized by the text parser."""

    name: str
    sets: list[SetData]
    warning: str | None = None


class ImportedWorkout(BaseModel):
    """A workout block recognized by the text parser."""

    name: str
    existing_id: str | None = None
    exercises: list[ImportedExercise]


class ImportPreview(BaseModel):
    """Result of parsing (and optionally applying) a bulk import."""

    workouts: list[ImportedWorkout]


class SessionSetData(BaseModel):
    """One set of a session, done or not."""

    model_config = ConfigDict(from_attributes=True)

    exercise_id: str | None = Field(default=None, max_length=36)
    exercise_name: str = Field(min_length=1, max_length=200)
    exercise_position: int = Field(ge=0, le=1000)
    set_index: int = Field(ge=0, le=100)
    weight_kg: float = Field(ge=0, le=2000)
    reps: int = Field(ge=0, le=1000)
    done: bool


class SessionIn(BaseModel):
    """A finished session as sent by the client (idempotent PUT by client id)."""

    workout_id: str | None = Field(default=None, max_length=36)
    workout_name: str = Field(min_length=1, max_length=120)
    started_at: AwareDatetime
    finished_at: AwareDatetime
    notes: str = Field(default="", max_length=2000)
    sets: list[SessionSetData] = Field(max_length=500)


class SessionSummary(BaseModel):
    """What the calendar needs about a session."""

    id: str
    workout_id: str | None
    workout_name: str
    workout_color: PlateColor | None
    started_at: UtcDatetime
    finished_at: UtcDatetime
    sets_done: int
    volume_kg: float


class SessionOut(SessionSummary):
    """A session with all its sets."""

    notes: str
    sets: list[SessionSetData]


class ExerciseSessionPoint(BaseModel):
    """The sets done for one exercise in one session."""

    session_id: str
    started_at: UtcDatetime
    sets: list[SetData]


class SnapshotBackup(BaseModel):
    """A history entry inside a backup file."""

    date: date
    sets: list[SetData]


class ExerciseBackup(ExerciseOut):
    """An exercise inside a backup file, including history."""

    snapshots: list[SnapshotBackup]


class WorkoutBackup(BaseModel):
    """A workout inside a backup file."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    position: int
    color: PlateColor = "red"
    exercises: list[ExerciseBackup]


class Backup(BaseModel):
    """Full data export."""

    version: int = 1
    workouts: list[WorkoutBackup]
    sessions: list["SessionBackup"] = []


class SessionBackup(SessionIn):
    """A session inside a backup file."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(min_length=1, max_length=36)
    # Naive values (from the database) are UTC; files carry an explicit offset.
    started_at: UtcDatetime
    finished_at: UtcDatetime


Backup.model_rebuild()

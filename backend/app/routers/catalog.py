"""Exercise library: search the shared catalog and add your own exercises."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.db import SessionDep
from app.models import CatalogExercise, Exercise, User, Workout
from app.schemas import CatalogCreate, CatalogItemOut, MuscleGroup
from app.services.catalog import search_key

DEFAULT_LIMIT = 60
MAX_LIMIT = 200

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("", response_model=list[CatalogItemOut])
def search_catalog(
    user: CurrentUser,
    session: SessionDep,
    q: Annotated[str, Query(max_length=100)] = "",
    group: MuscleGroup | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> list[CatalogItemOut]:
    """Search by name (Portuguese or English, any word order, accents ignored).

    The user's own exercises and the ones already in their workouts come first.
    """
    query = select(CatalogExercise).where(visible_to(user))
    for token in search_key(q).split():
        query = query.where(CatalogExercise.search_text.contains(token, autoescape=True))
    if group is not None:
        query = query.where(CatalogExercise.muscle_group == group)
    uses = _usage_counts(session, user)
    items = sorted(
        session.scalars(query),
        key=lambda item: (-uses.get(item.id, 0), item.user_id is None, item.name_pt.lower()),
    )
    return [_to_out(item, uses.get(item.id, 0)) for item in items[:limit]]


@router.post("", response_model=CatalogItemOut, status_code=status.HTTP_201_CREATED)
def create_custom_exercise(payload: CatalogCreate, user: CurrentUser, session: SessionDep) -> CatalogItemOut:
    """Add an exercise only this user sees; replays with the same id are no-ops.

    Raises:
        HTTPException: 409 when the id is taken by the library or another user.
    """
    existing = session.get(CatalogExercise, payload.id)
    if existing is not None:
        if existing.user_id != user.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Identificador já em uso")
        return _to_out(existing, 0)
    item = CatalogExercise(
        id=payload.id,
        user_id=user.id,
        name_pt=payload.name.strip(),
        name_en="",
        muscle_group=payload.muscle_group,
        equipment=payload.equipment.strip(),
        images=[],
        search_text=search_key(payload.name),
    )
    session.add(item)
    session.flush()
    return _to_out(item, 0)


def visible_to(user: User):
    """SQL condition: shared library entries plus the user's own."""
    return or_(CatalogExercise.user_id.is_(None), CatalogExercise.user_id == user.id)


def visible_catalog_id(session: Session, user: User, catalog_id: str | None) -> str | None:
    """``catalog_id`` when the user may use it, otherwise None (unknown or someone else's)."""
    item = session.get(CatalogExercise, catalog_id) if catalog_id else None
    if item is None or (item.user_id is not None and item.user_id != user.id):
        return None
    return item.id


def _usage_counts(session: Session, user: User) -> dict[str, int]:
    """How many of the user's exercises point at each catalog entry."""
    rows = session.execute(
        select(Exercise.catalog_id, func.count())
        .join(Workout)
        .where(Workout.user_id == user.id, Exercise.catalog_id.is_not(None))
        .group_by(Exercise.catalog_id)
    )
    return {catalog_id: count for catalog_id, count in rows}


def _to_out(item: CatalogExercise, uses: int) -> CatalogItemOut:
    """Serialize a catalog row for the picker."""
    return CatalogItemOut(
        id=item.id,
        name=item.name_pt,
        name_en=item.name_en,
        muscle_group=item.muscle_group,
        equipment=item.equipment,
        images=list(item.images),
        custom=item.user_id is not None,
        uses=uses,
    )

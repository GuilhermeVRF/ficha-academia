"""Database engine, session factory and declarative base."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_session() -> Iterator[Session]:
    """Yield a session for one request, committing on success."""
    with SessionLocal() as session:
        yield session
        session.commit()


# "function" scope commits before the response is sent; the default would commit
# afterwards, letting the client's next request (e.g. an outbox PUT right after a
# POST) read stale data.
SessionDep = Annotated[Session, Depends(get_session, scope="function")]

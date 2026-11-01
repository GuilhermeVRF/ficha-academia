"""The admin account, defined by environment variables instead of a signup."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import normalize_email, password_hasher, utcnow
from app.models import User, Workout


def ensure_admin(session: Session, name: str, email: str, password: str) -> User:
    """Create or update the admin so it matches the environment, then give it ownerless workouts.

    Safe to run on every start: an existing account is promoted to admin and
    its name and password follow the environment (the password is only
    re-hashed when it changed).

    Args:
        session: Active database session; the caller commits.
        name: Display name for the admin.
        email: Admin login email.
        password: Admin password in plain text, as read from the environment.

    Returns:
        The admin user.
    """
    email = normalize_email(email)
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            password_hash=password_hasher.hash(password),
            is_admin=True,
            created_at=utcnow(),
        )
        session.add(user)
        session.flush()
    else:
        user.name = name
        user.is_admin = True
        if not password_hasher.verify(password, user.password_hash):
            user.password_hash = password_hasher.hash(password)
    # Workouts from before accounts existed have no owner; they belong to the admin.
    session.execute(update(Workout).where(Workout.user_id.is_(None)).values(user_id=user.id))
    return user

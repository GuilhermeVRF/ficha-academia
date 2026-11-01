"""Invite codes that let friends create an account."""

import secrets
from datetime import UTC, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth import CurrentUser, utcnow
from app.db import SessionDep
from app.models import Invite, User
from app.schemas import InviteOut

INVITE_LIFETIME = timedelta(days=7)
INVITE_LIST_LIMIT = 20

router = APIRouter(prefix="/invites", tags=["invites"])


def require_admin(user: CurrentUser) -> User:
    """FastAPI dependency allowing only admins.

    Raises:
        HTTPException: 403 for regular users.
    """
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só o administrador pode convidar.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


@router.post("", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
def create_invite(admin: AdminUser, session: SessionDep) -> InviteOut:
    """Create a single-use invite valid for a week."""
    now = utcnow()
    invite = Invite(
        code=secrets.token_urlsafe(9),
        created_by_id=admin.id,
        created_at=now,
        expires_at=now + INVITE_LIFETIME,
    )
    session.add(invite)
    session.flush()
    return _to_out(invite)


@router.get("", response_model=list[InviteOut])
def list_invites(admin: AdminUser, session: SessionDep) -> list[InviteOut]:
    """List the admin's most recent invites, newest first."""
    invites = session.scalars(
        select(Invite)
        .where(Invite.created_by_id == admin.id)
        .order_by(Invite.created_at.desc())
        .limit(INVITE_LIST_LIMIT)
    )
    return [_to_out(invite) for invite in invites]


def _to_out(invite: Invite) -> InviteOut:
    """Serialize with explicit UTC so the client shows local times correctly."""
    return InviteOut(
        code=invite.code,
        created_at=invite.created_at.replace(tzinfo=UTC),
        expires_at=invite.expires_at.replace(tzinfo=UTC),
        used_by_name=invite.used_by.name if invite.used_by else None,
    )

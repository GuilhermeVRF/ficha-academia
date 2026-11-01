"""Email/password accounts with server-side sessions and invite-only signup."""

import hashlib
import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionDep
from app.models import Invite, User, UserSession
from app.schemas import LoginRequest, SignupRequest, UserOut

COOKIE_NAME = "pino_session"
SESSION_LIFETIME = timedelta(days=365)
MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60

router = APIRouter(prefix="/auth", tags=["auth"])
password_hasher = PasswordHash.recommended()
# Verified for unknown emails so response time doesn't reveal which accounts exist.
_DUMMY_HASH = password_hasher.hash("pino-dummy-password")


class LoginThrottle:
    """Counts recent failed logins per email; in memory, which fits a single instance."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self._limit = limit
        self._window = window_seconds
        self._failures: defaultdict[str, deque[float]] = defaultdict(deque)

    def is_blocked(self, key: str) -> bool:
        """Whether ``key`` reached the failure limit inside the window."""
        failures = self._failures[key]
        cutoff = time.monotonic() - self._window
        while failures and failures[0] < cutoff:
            failures.popleft()
        return len(failures) >= self._limit

    def record_failure(self, key: str) -> None:
        """Count one failed attempt for ``key``."""
        self._failures[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        """Forget the failures of ``key`` after a successful login."""
        self._failures.pop(key, None)

    def clear(self) -> None:
        """Forget every failure."""
        self._failures.clear()


login_throttle = LoginThrottle(MAX_FAILED_LOGINS, FAILED_LOGIN_WINDOW_SECONDS)


def current_user(
    session: SessionDep,
    token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> User:
    """FastAPI dependency returning the signed-in user.

    Raises:
        HTTPException: 401 when the cookie is missing, unknown or expired.
    """
    row = session.get(UserSession, _hash_token(token)) if token else None
    if row is None or row.expires_at <= utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Entre de novo.")
    return row.user


CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, session: SessionDep, response: Response) -> User:
    """Create an account from an invite and sign it in.

    The admin is never created here; it comes from the environment (see services.admin).

    Raises:
        HTTPException: 403 for a missing/used/expired invite, 409 for a taken email.
    """
    invite = _usable_invite(session, payload.invite_code)
    email = normalize_email(payload.email)
    if session.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com este e-mail.")

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        name=payload.name.strip(),
        password_hash=password_hasher.hash(payload.password),
        is_admin=False,
        created_at=utcnow(),
    )
    session.add(user)
    session.flush()
    invite.used_by_id = user.id
    _start_session(session, user, response)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, session: SessionDep, response: Response) -> User:
    """Check email and password and start a session.

    Raises:
        HTTPException: 429 after too many recent failures, 401 for wrong credentials.
    """
    email = normalize_email(payload.email)
    if login_throttle.is_blocked(email):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitas tentativas. Espere alguns minutos.")
    user = session.scalar(select(User).where(User.email == email))
    password_ok = password_hasher.verify(payload.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not password_ok:
        login_throttle.record_failure(email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    login_throttle.reset(email)
    _start_session(session, user, response)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session: SessionDep,
    response: Response,
    token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> None:
    """End this device's session; other devices stay signed in."""
    if token:
        session.execute(delete(UserSession).where(UserSession.token_hash == _hash_token(token)))
    response.delete_cookie(COOKIE_NAME)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    """Return the signed-in user (401 when signed out)."""
    return user


def normalize_email(email: str) -> str:
    """Compare emails case-insensitively and without surrounding spaces."""
    return email.strip().lower()


def utcnow() -> datetime:
    """Current UTC time as a naive datetime, which is how the database stores it."""
    return datetime.now(UTC).replace(tzinfo=None)


def _usable_invite(session: Session, code: str | None) -> Invite:
    """Load an invite that can still be used.

    Raises:
        HTTPException: 403 when the code is missing, unknown, used or expired.
    """
    invite = session.get(Invite, code.strip()) if code else None
    if invite is None or invite.used_by_id is not None or invite.expires_at <= utcnow():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Convite inválido, já usado ou expirado.")
    return invite


def _start_session(session: Session, user: User, response: Response) -> None:
    """Store a new session (dropping this user's expired ones) and set its cookie."""
    now = utcnow()
    session.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    session.add(UserSession(token_hash=_hash_token(token), user_id=user.id, expires_at=now + SESSION_LIFETIME))
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookie,
    )


def _hash_token(token: str) -> str:
    """Sessions are stored by hash so a database leak can't be replayed as cookies."""
    return hashlib.sha256(token.encode()).hexdigest()

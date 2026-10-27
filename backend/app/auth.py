"""Single-user password auth backed by a signed, long-lived cookie."""

import hashlib
import hmac
import logging
import time

from fastapi import APIRouter, Cookie, HTTPException, Response, status

from app.config import settings
from app.schemas import LoginRequest

logger = logging.getLogger(__name__)

COOKIE_NAME = "ficha_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365
FAILED_LOGIN_DELAY_SECONDS = 1.0

router = APIRouter(prefix="/auth", tags=["auth"])

if not settings.app_password:
    logger.warning("APP_PASSWORD is not set: authentication is disabled")


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(payload: LoginRequest, response: Response) -> None:
    """Validate the password and set the session cookie."""
    if not hmac.compare_digest(payload.password.encode(), settings.app_password.encode()):
        # Slows down brute force without needing a rate limiter for a single-user app.
        time.sleep(FAILED_LOGIN_DELAY_SECONDS)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Senha incorreta")
    response.set_cookie(
        COOKIE_NAME,
        _session_token(),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookie,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Clear the session cookie."""
    response.delete_cookie(COOKIE_NAME)


@router.get("/me", status_code=status.HTTP_204_NO_CONTENT)
def me(ficha_session: str | None = Cookie(default=None)) -> None:
    """Report whether the current cookie is valid (204) or not (401)."""
    require_session(ficha_session)


def require_session(ficha_session: str | None = Cookie(default=None)) -> None:
    """FastAPI dependency rejecting requests without a valid session cookie.

    Raises:
        HTTPException: 401 when auth is enabled and the cookie is missing or invalid.
    """
    if not settings.app_password:
        return
    if ficha_session is None or not hmac.compare_digest(ficha_session, _session_token()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")


def _session_token() -> str:
    """Derive the session token; changing the password invalidates old cookies."""
    return hmac.new(
        settings.secret_key.encode(),
        settings.app_password.encode(),
        hashlib.sha256,
    ).hexdigest()

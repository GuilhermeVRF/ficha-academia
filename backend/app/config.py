"""Runtime settings read from environment variables."""

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

DEV_SECRET_KEY = "dev-secret-change-me"


@dataclass(frozen=True)
class Settings:
    """Application settings.

    Attributes:
        database_url: SQLAlchemy URL, normalized to the psycopg 3 driver.
        app_password: Single-user password. Empty disables auth (local dev only).
        secret_key: Key used to sign the session cookie.
        timezone: Zone used to decide which calendar day an edit belongs to.
        static_dir: Built frontend directory served at "/", if it exists.
        secure_cookie: Whether the session cookie requires HTTPS.
    """

    database_url: str
    app_password: str
    secret_key: str
    timezone: ZoneInfo
    static_dir: str
    secure_cookie: bool


def load_settings() -> Settings:
    """Build settings from the current environment.

    Raises:
        RuntimeError: If production mode (secure cookie) lacks a password or secret key.
    """
    loaded = Settings(
        database_url=_normalize_database_url(os.environ.get("DATABASE_URL", "sqlite:///./dev.db")),
        app_password=os.environ.get("APP_PASSWORD", ""),
        secret_key=os.environ.get("SECRET_KEY", DEV_SECRET_KEY),
        timezone=ZoneInfo(os.environ.get("APP_TIMEZONE", "America/Sao_Paulo")),
        static_dir=os.environ.get("STATIC_DIR", "../frontend/dist"),
        secure_cookie=os.environ.get("SECURE_COOKIE", "false").lower() == "true",
    )
    if loaded.secure_cookie:
        _require_production_secrets(loaded)
    return loaded


def _require_production_secrets(loaded: Settings) -> None:
    """Refuse to start in production with auth disabled or a known signing key."""
    missing = []
    if not loaded.app_password:
        missing.append("APP_PASSWORD")
    if not loaded.secret_key or loaded.secret_key == DEV_SECRET_KEY:
        missing.append("SECRET_KEY")
    if missing:
        raise RuntimeError(f"Missing required production settings: {', '.join(missing)}")


def _normalize_database_url(url: str) -> str:
    """Point Postgres URLs (as Railway provides them) at the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


settings = load_settings()

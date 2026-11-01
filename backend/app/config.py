"""Runtime settings read from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

MIN_ADMIN_PASSWORD_LENGTH = 8
LOCAL_DATABASE_URL = "postgresql://pino:pino@localhost:5432/pino"

# Local development reads backend/.env; real environment variables (Railway) always win.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass(frozen=True)
class Settings:
    """Application settings.

    Attributes:
        database_url: SQLAlchemy URL, normalized to the psycopg 3 driver.
        timezone: Zone used to decide which calendar day an edit belongs to.
        static_dir: Built frontend directory served at "/", if it exists.
        secure_cookie: Whether the session cookie requires HTTPS.
        admin_name: Display name of the admin account managed by the environment.
        admin_email: Admin login; empty disables the managed admin (tests only).
        admin_password: Admin password; the environment is the source of truth.
    """

    database_url: str
    timezone: ZoneInfo
    static_dir: str
    secure_cookie: bool
    admin_name: str
    admin_email: str
    admin_password: str


def load_settings() -> Settings:
    """Build settings from the current environment.

    Raises:
        RuntimeError: In production (secure cookie) without a usable admin account.
    """
    loaded = Settings(
        database_url=_normalize_database_url(os.environ.get("DATABASE_URL", LOCAL_DATABASE_URL)),
        timezone=ZoneInfo(os.environ.get("APP_TIMEZONE", "America/Sao_Paulo")),
        static_dir=os.environ.get("STATIC_DIR", "../frontend/dist"),
        secure_cookie=os.environ.get("SECURE_COOKIE", "false").lower() == "true",
        admin_name=os.environ.get("ADMIN_NAME", "Admin").strip() or "Admin",
        admin_email=os.environ.get("ADMIN_EMAIL", "").strip(),
        admin_password=os.environ.get("ADMIN_PASSWORD", ""),
    )
    if loaded.secure_cookie:
        _require_admin(loaded)
    return loaded


def _require_admin(loaded: Settings) -> None:
    """Without an admin nobody could invite anyone, so production refuses to start."""
    missing = []
    if not loaded.admin_email:
        missing.append("ADMIN_EMAIL")
    if len(loaded.admin_password) < MIN_ADMIN_PASSWORD_LENGTH:
        missing.append(f"ADMIN_PASSWORD (min. {MIN_ADMIN_PASSWORD_LENGTH} caracteres)")
    if missing:
        raise RuntimeError(f"Missing required production settings: {', '.join(missing)}")


def _normalize_database_url(url: str) -> str:
    """Point Postgres URLs (as Railway provides them) at the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


settings = load_settings()

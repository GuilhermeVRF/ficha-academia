"""Tests for production settings validation."""

import pytest

from app.config import load_settings


def test_production_requires_password_and_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secure mode without secrets fails fast, naming every missing variable."""
    monkeypatch.setenv("SECURE_COOKIE", "true")
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="APP_PASSWORD, SECRET_KEY"):
        load_settings()


def test_production_accepts_configured_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secure mode loads normally once both secrets are set."""
    monkeypatch.setenv("SECURE_COOKIE", "true")
    monkeypatch.setenv("APP_PASSWORD", "s3nha")
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    assert load_settings().secure_cookie


def test_dev_mode_allows_missing_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Local development keeps working without any secrets."""
    monkeypatch.delenv("SECURE_COOKIE", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert load_settings().app_password == ""

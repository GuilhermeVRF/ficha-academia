"""Tests for production settings validation."""

import pytest

from app.config import load_settings


def test_production_requires_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without an admin nobody could invite anyone, so production refuses to start."""
    monkeypatch.setenv("SECURE_COOKIE", "true")
    monkeypatch.setenv("ADMIN_EMAIL", "")
    monkeypatch.setenv("ADMIN_PASSWORD", "curta")
    with pytest.raises(RuntimeError, match="ADMIN_EMAIL, ADMIN_PASSWORD"):
        load_settings()


def test_production_accepts_configured_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECURE_COOKIE", "true")
    monkeypatch.setenv("ADMIN_EMAIL", "gui@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-1")
    assert load_settings().admin_email == "gui@example.com"


def test_dev_mode_allows_missing_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECURE_COOKIE", "false")
    monkeypatch.setenv("ADMIN_EMAIL", "")
    assert load_settings().admin_email == ""

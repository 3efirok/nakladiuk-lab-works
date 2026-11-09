"""Configuration from environment variables (lab 10)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from experiment_registry.persistence.database import get_database_url
from experiment_registry.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def fresh_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    for name in ("DATABASE_URL", "ENVIRONMENT", "APP_ENV", "LOG_LEVEL", "API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)  # no stray .env file can influence the test
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults_are_safe_for_development() -> None:
    settings = Settings()

    assert settings.environment == "development"
    assert settings.database_url == "sqlite:///experiments.db"
    assert settings.log_level == "INFO" and settings.api_token is None


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:////data/experiments.db")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    settings = get_settings()

    assert settings.database_url == "sqlite:////data/experiments.db"
    assert settings.is_production and settings.log_level == "WARNING"
    assert get_database_url() == "sqlite:////data/experiments.db"


def test_invalid_values_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")

    with pytest.raises(ValidationError):
        Settings()


def test_secret_is_not_revealed_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_TOKEN", "super-secret-value")

    settings = Settings()

    assert settings.api_token is not None
    assert settings.api_token.get_secret_value() == "super-secret-value"
    assert "super-secret-value" not in repr(settings)

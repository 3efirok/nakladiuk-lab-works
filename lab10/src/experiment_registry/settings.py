"""Application settings from environment variables (12-factor configuration).

Values are read from the process environment and, for local development, from a `.env`
file that is never committed to Git. Secrets use `SecretStr`, so they are not printed
in logs, reprs or tracebacks.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Experiment Registry"
    environment: Literal["development", "test", "production"] = Field(
        default="development", validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV")
    )
    database_url: str = "sqlite:///experiments.db"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_token: SecretStr | None = Field(
        default=None, description="If set, POST/PATCH/DELETE require the X-API-Token header."
    )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Settings are created once per process; tests call get_settings.cache_clear()."""
    return Settings()

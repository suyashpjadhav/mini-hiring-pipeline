"""Application settings configuration using pydantic-settings."""

import functools
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    app_env: Literal["dev", "test", "prod"] = "dev"
    debug: bool = False
    database_url: str = "sqlite:///./var/app.db"
    app_default_tz: str = "Asia/Kolkata"
    job_title: str = "Senior Backend Engineer"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    llm_timeout_s: float = 4.0
    llm_thinking_budget: int = 0
    llm_max_calls_per_min: int = 30
    telemetry_log_queries: bool = False
    telemetry_path: str = "var/telemetry.jsonl"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("app_default_tz")
    @classmethod
    def validate_app_default_tz(cls, v: str) -> str:
        """Validate that app_default_tz is a valid IANA time zone."""
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as err:
            raise ValueError(f"Invalid IANA time zone: '{v}'") from err
        return v

    @property
    def llm_enabled(self) -> bool:
        """Return True if Gemini API key is present and non-empty."""
        if self.gemini_api_key is None:
            return False
        return bool(self.gemini_api_key.get_secret_value().strip())


@functools.lru_cache
def get_settings() -> Settings:
    """Get cached application settings instance."""
    return Settings()

"""Unit tests for Settings configuration."""

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test default values of Settings."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings()
    assert settings.app_env == "dev"
    assert settings.debug is False
    assert settings.database_url == "sqlite:///./var/app.db"
    assert settings.app_default_tz == "Asia/Kolkata"
    assert settings.job_title == "Senior Backend Engineer"
    assert settings.gemini_model == "gemini-2.5-flash"
    assert settings.llm_timeout_s == 3.0
    assert settings.llm_max_calls_per_min == 30
    assert settings.telemetry_log_queries is False


def test_invalid_app_default_tz_raises() -> None:
    """Test setting an invalid IANA time zone raises ValidationError."""
    with pytest.raises(ValidationError, match="Invalid IANA time zone"):
        Settings(app_default_tz="Invalid/Zone_Name")


def test_llm_enabled_property() -> None:
    """Test llm_enabled property returns False when key is missing or empty."""
    settings_no_key = Settings(gemini_api_key=None)
    assert settings_no_key.llm_enabled is False

    settings_empty_key = Settings(gemini_api_key=SecretStr("   "))
    assert settings_empty_key.llm_enabled is False

    settings_with_key = Settings(gemini_api_key=SecretStr("AIzaSyTestKey123456789"))
    assert settings_with_key.llm_enabled is True


def test_gemini_api_key_secret_repr() -> None:
    """Test gemini_api_key SecretStr is never shown in string representation or repr."""
    raw_key = "AIzaSySecretTestKey9999999"
    settings = Settings(gemini_api_key=SecretStr(raw_key))
    assert raw_key not in repr(settings)
    assert raw_key not in str(settings)
    if settings.gemini_api_key is not None:
        assert raw_key not in repr(settings.gemini_api_key)
        assert raw_key not in str(settings.gemini_api_key)

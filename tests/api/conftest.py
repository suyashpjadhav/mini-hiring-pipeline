"""Pytest fixtures for API v1 test suite."""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.core.config import Settings
from app.main import create_app

NOW_A = datetime(2026, 9, 30, 14, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))


@pytest.fixture
def test_clock() -> FixedClock:
    """Provide a FixedClock set to NOW_A."""
    return FixedClock(NOW_A)


@pytest.fixture
def client(tmp_path: Path, test_clock: FixedClock) -> Generator[TestClient, None, None]:
    """Provide a TestClient with a fresh temporary SQLite database and running lifespan."""
    db_file = tmp_path / "api_test.db"
    settings = Settings(database_url=f"sqlite:///{db_file}")
    app = create_app(settings=settings, clock=test_clock)

    with TestClient(app) as test_client:
        yield test_client

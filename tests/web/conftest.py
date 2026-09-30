"""Pytest fixtures for Web test suite."""

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_clock() -> FixedClock:
    """Provide a FixedClock set to current UTC time."""
    return FixedClock(datetime.now(UTC))


@pytest.fixture
def client(tmp_path: Path, test_clock: FixedClock) -> Generator[TestClient, None, None]:
    """Provide a TestClient with a fresh temporary SQLite database and running lifespan."""
    db_file = tmp_path / "web_test.db"
    settings = Settings(app_env="test", database_url=f"sqlite:///{db_file}")
    app = create_app(settings=settings, clock=test_clock)

    with TestClient(app) as test_client:
        yield test_client

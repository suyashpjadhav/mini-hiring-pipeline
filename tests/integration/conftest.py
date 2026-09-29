"""Integration test fixtures for database, clock, and service."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.core.clock import FixedClock
from app.core.db import create_engine_for, run_migrations
from app.features.pipeline.service import PipelineService

# NOW_A: 2026-09-30T14:00:00+05:30 = 2026-09-30T08:30:00Z
NOW_A = datetime(2026, 9, 30, 8, 30, tzinfo=UTC)


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    """Return a file-based SQLite database URL in tmp_path."""
    db_file = tmp_path / "test.db"
    return f"sqlite:///{db_file}"


@pytest.fixture
def engine(db_url: str) -> Engine:
    """Run migrations and return a configured engine instance."""
    run_migrations(db_url)
    return create_engine_for(db_url)


@pytest.fixture
def fixed_clock() -> FixedClock:
    """Return a FixedClock set at reference timestamp NOW_A."""
    return FixedClock(NOW_A)


@pytest.fixture
def pipeline_service(engine: Engine, fixed_clock: FixedClock) -> PipelineService:
    """Return a PipelineService initialized with the test engine and fixed clock."""
    return PipelineService(engine, fixed_clock)

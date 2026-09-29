"""Integration tests for seed dataset generation and anchor resolution (TEST_PLAN Step 9)."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.core.clock import FixedClock
from app.core.db import create_engine_for, run_migrations
from app.features.pipeline.service import PipelineService
from scripts.seed import seed_database

NOW_A = datetime(2026, 9, 30, 14, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
MONDAY_0005 = datetime(2026, 9, 28, 0, 5, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
TZ_KOLKATA = ZoneInfo("Asia/Kolkata")
SEED_DATA_PATH = Path("scripts/seed_data.json")


def test_seed_database_at_now_a(tmp_path: Path) -> None:
    """Test seeding database at NOW_A produces 26 candidates and exact board counts."""
    db_file = tmp_path / "seed_now_a.db"
    db_url = f"sqlite:///{db_file}"
    run_migrations(db_url)
    engine = create_engine_for(db_url)

    # 1. Seed database
    key_map = seed_database(engine, SEED_DATA_PATH, NOW_A, TZ_KOLKATA)
    assert len(key_map) == 26

    # 2. Check board column counts
    clock = FixedClock(NOW_A)
    service = PipelineService(engine, clock)
    board = service.board()

    assert len(board.applied) == 2
    assert len(board.screening) == 8
    assert len(board.interview) == 4
    assert len(board.offer) == 3
    assert len(board.hired) == 2
    assert len(board.rejected) == 7

    # 3. rebuild_diff is empty
    diffs = service.rebuild_diff()
    assert diffs == []

    # 4. Every chain verifies
    for cid in key_map.values():
        res = service.verify(cid)
        assert res.valid is True
        assert res.broken_at_seq is None

    # 5. Re-seeding without reset fails
    with pytest.raises(RuntimeError, match="Database already has 26 candidates; use --reset"):
        seed_database(engine, SEED_DATA_PATH, NOW_A, TZ_KOLKATA)


def test_seed_database_at_monday_0005(tmp_path: Path) -> None:
    """Test seeding database at Monday 00:05 IST succeeds (anchor-fraction robustness)."""
    db_file = tmp_path / "seed_monday.db"
    db_url = f"sqlite:///{db_file}"
    run_migrations(db_url)
    engine = create_engine_for(db_url)

    key_map = seed_database(engine, SEED_DATA_PATH, MONDAY_0005, TZ_KOLKATA)
    assert len(key_map) == 26

    clock = FixedClock(MONDAY_0005)
    service = PipelineService(engine, clock)
    diffs = service.rebuild_diff()
    assert diffs == []

    for cid in key_map.values():
        res = service.verify(cid)
        assert res.valid is True

"""Database seeding script and reusable seeder module (SYSTEM_DESIGN §14)."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import Engine

from app.core.clock import FixedClock
from app.core.config import get_settings
from app.core.db import create_engine_for, read_tx, run_migrations
from app.features.pipeline.domain.stages import Action
from app.features.pipeline.repo import PipelineRepo
from app.features.pipeline.service import PipelineService


class SeedTimeAnchor(BaseModel):
    """Anchor specifier for seeding timestamps."""

    anchor: Literal["now", "monday"]
    offset_hours: float | None = None
    fraction: float | None = None


class SeedEvent(BaseModel):
    """Seed event specification."""

    action: Literal["create", "advance", "reject", "note"]
    at: SeedTimeAnchor
    note: str | None = None


class SeedCandidate(BaseModel):
    """Seed candidate specification."""

    key: str
    full_name: str
    email: str | None = None
    purpose: str
    events: list[SeedEvent]


class SeedData(BaseModel):
    """Root model for seed_data.json."""

    version: int
    anchors: dict[str, str]
    candidates: list[SeedCandidate]


def resolve_anchor_time(
    anchor: SeedTimeAnchor,
    now: datetime,
    tz: ZoneInfo,
) -> datetime:
    """Resolve absolute timestamp from relative anchor specification."""
    now_tz = now.astimezone(tz)
    if anchor.anchor == "now":
        if anchor.offset_hours is None:
            raise ValueError("offset_hours required when anchor is 'now'")
        return now_tz + timedelta(hours=anchor.offset_hours)
    elif anchor.anchor == "monday":
        if anchor.fraction is None:
            raise ValueError("fraction required when anchor is 'monday'")
        monday_0000 = now_tz.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=now_tz.weekday()
        )
        elapsed_seconds = (now_tz - monday_0000).total_seconds()
        return monday_0000 + timedelta(seconds=anchor.fraction * elapsed_seconds)
    else:
        raise ValueError(f"Unknown anchor type '{anchor.anchor}'")


def seed_database(
    engine: Engine,
    data_path: Path,
    now: datetime,
    tz: ZoneInfo,
) -> dict[str, str]:
    """Seed database using PipelineService and a stepping FixedClock.

    Returns mapping of seed key -> candidate ULID id.
    """
    with read_tx(engine) as conn:
        repo = PipelineRepo(conn)
        existing_ids = repo.list_candidate_ids()

    if existing_ids:
        raise RuntimeError(f"Database already has {len(existing_ids)} candidates; use --reset")

    raw_json = data_path.read_text(encoding="utf-8")
    seed_data = SeedData.model_validate_json(raw_json)

    clock = FixedClock(now)
    service = PipelineService(engine, clock)
    key_to_id: dict[str, str] = {}

    for cand in seed_data.candidates:
        if not cand.events:
            raise ValueError(f"Candidate '{cand.key}' has no events in seed data")

        resolved_times: list[datetime] = []
        for ev in cand.events:
            t = resolve_anchor_time(ev.at, now, tz)
            resolved_times.append(t)

        for i in range(1, len(resolved_times)):
            if resolved_times[i] <= resolved_times[i - 1]:
                msg = (
                    f"Candidate '{cand.key}' event #{i} at {resolved_times[i]} "
                    f"is not strictly after previous event at {resolved_times[i - 1]}"
                )
                raise ValueError(msg)

        if resolved_times[-1] > now.astimezone(tz):
            msg = (
                f"Candidate '{cand.key}' final event time {resolved_times[-1]} "
                f"is in the future (> {now})"
            )
            raise ValueError(msg)

        # First event must be create
        first_evt = cand.events[0]
        if first_evt.action != "create":
            raise ValueError(f"Candidate '{cand.key}' first event must be 'create'")

        clock.set(resolved_times[0])
        created = service.create_candidate(full_name=cand.full_name, email=cand.email)
        cand_id = created.id
        key_to_id[cand.key] = cand_id

        curr_version = created.version
        for idx in range(1, len(cand.events)):
            evt = cand.events[idx]
            evt_time = resolved_times[idx]
            clock.set(evt_time)

            if evt.action == "advance":
                res = service.transition(
                    candidate_id=cand_id,
                    action=Action.ADVANCE,
                    expected_version=curr_version,
                    note=evt.note,
                )
                curr_version = res.version
            elif evt.action == "reject":
                res = service.transition(
                    candidate_id=cand_id,
                    action=Action.REJECT,
                    expected_version=curr_version,
                    note=evt.note,
                )
                curr_version = res.version
            elif evt.action == "note":
                if not evt.note:
                    raise ValueError(f"Candidate '{cand.key}' note event missing text")
                res = service.add_note(candidate_id=cand_id, text=evt.note)
                curr_version = res.version
            else:
                raise ValueError(f"Unknown action '{evt.action}' for candidate '{cand.key}'")

    return key_to_id


def main() -> None:
    """CLI entrypoint for seeding pipeline database."""
    parser = argparse.ArgumentParser(description="Seed mini-hiring-pipeline database.")
    parser.add_argument(
        "--reset", action="store_true", help="Delete existing database before seeding."
    )
    parser.add_argument("--now", type=str, default=None, help="Optional ISO8601 datetime for NOW.")
    parser.add_argument("--tz", type=str, default=None, help="Optional timezone name.")

    args = parser.parse_args()
    settings = get_settings()
    tz_name = args.tz or settings.app_default_tz
    tz = ZoneInfo(tz_name)

    if args.now:
        now = datetime.fromisoformat(args.now)
        now = now.replace(tzinfo=tz) if now.tzinfo is None else now.astimezone(tz)
    else:
        now = datetime.now(tz)

    db_url = settings.database_url
    if args.reset and db_url.startswith("sqlite:///"):
        db_path_str = db_url.replace("sqlite:///", "")
        db_path = Path(db_path_str)
        if db_path.exists():
            db_path.unlink()
        wal_path = Path(f"{db_path_str}-wal")
        if wal_path.exists():
            wal_path.unlink()
        shm_path = Path(f"{db_path_str}-shm")
        if shm_path.exists():
            shm_path.unlink()

    run_migrations(db_url)
    engine = create_engine_for(db_url)

    data_path = Path(__file__).parent / "seed_data.json"
    try:
        key_map = seed_database(engine, data_path, now, tz)
    except RuntimeError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    service = PipelineService(engine, FixedClock(now))
    board = service.board()
    diffs = service.rebuild_diff()

    verified_count = 0
    for cand_id in key_map.values():
        res = service.verify(cand_id)
        if res.valid:
            verified_count += 1

    total_events = 0
    with read_tx(engine) as conn:
        repo = PipelineRepo(conn)
        for cand_id in key_map.values():
            events = repo.get_events(cand_id)
            total_events += len(events)

    diff_status = "OK (0 differences)" if not diffs else f"FAILED ({len(diffs)} diffs)"

    print("=== SEED SUMMARY ===")
    print(f"Candidates created : {len(key_map)}")
    print(f"Events appended    : {total_events}")
    print(
        f"Board columns      : Applied: {len(board.applied)}, "
        f"Screening: {len(board.screening)}, Interview: {len(board.interview)}, "
        f"Offer: {len(board.offer)}, Hired: {len(board.hired)}, "
        f"Rejected: {len(board.rejected)}"
    )
    print(f"Rebuild diff       : {diff_status}")
    print(f"Chains verified    : {verified_count}/{len(key_map)} verified")


if __name__ == "__main__":
    main()

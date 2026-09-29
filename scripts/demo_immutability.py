"""Demo script attempting illegal DB changes to prove audit immutability (SYSTEM_DESIGN §9)."""

import sqlite3
import sys
from pathlib import Path

from app.core.clock import SystemClock
from app.core.config import get_settings
from app.core.db import create_engine_for, read_tx
from app.features.pipeline.repo import PipelineRepo
from app.features.pipeline.service import PipelineService


def main() -> None:
    """Run raw SQLite mutation attempts and verify database triggers block all of them."""
    settings = get_settings()
    db_url = settings.database_url

    if not db_url.startswith("sqlite:///"):
        print("Error: demo_immutability requires a SQLite database URL", file=sys.stderr)
        sys.exit(1)

    db_path_str = db_url.replace("sqlite:///", "")
    db_path = Path(db_path_str)

    if not db_path.exists():
        err_msg = f"Error: Database file '{db_path}' does not exist. Run scripts/seed.py first."
        print(err_msg, file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    print("=== DEMO IMMUTABILITY: ATTEMPTING ILLEGAL MUTATIONS ===")

    # 1. UPDATE stage_events
    try:
        conn.execute("UPDATE stage_events SET note='edited' WHERE seq=1;")
        conn.commit()
    except sqlite3.Error as err:
        print(f"BLOCKED by the database: {err}")

    # 2. DELETE FROM stage_events
    try:
        conn.execute("DELETE FROM stage_events WHERE seq=1;")
        conn.commit()
    except sqlite3.Error as err:
        print(f"BLOCKED by the database: {err}")

    # 3. UPDATE candidates
    try:
        conn.execute("UPDATE candidates SET full_name='X';")
        conn.commit()
    except sqlite3.Error as err:
        print(f"BLOCKED by the database: {err}")

    # 4. Illegal INSERT skipping Applied -> Interview
    cursor = conn.execute("SELECT id FROM candidates LIMIT 1;")
    row = cursor.fetchone()
    if row:
        cand_id = row[0]
        try:
            conn.execute(
                """
                INSERT INTO stage_events
                  (id, candidate_id, seq, type, from_stage, to_stage, occurred_at, actor, hash)
                VALUES
                  ('01H00000000000000000000099', ?, 99, 'ADVANCED', 'Applied', 'Interview',
                   1000000000000, 'recruiter', 'fakehash');
                """,
                (cand_id,),
            )
            conn.commit()
        except sqlite3.Error as err:
            print(f"BLOCKED by the database: {err}")

    conn.close()

    # Verify history intact
    engine = create_engine_for(db_url)
    clock = SystemClock()
    service = PipelineService(engine, clock)

    total_events = 0
    all_valid = True
    with read_tx(engine) as tx_conn:
        repo = PipelineRepo(tx_conn)
        cand_ids = repo.list_candidate_ids()
        for cid in cand_ids:
            events = repo.get_events(cid)
            total_events += len(events)
            v = service.verify(cid)
            if not v.valid:
                all_valid = False

    if all_valid:
        print(f"\nHistory intact: {total_events} events, all chains verified")
    else:
        print("\nERROR: Verification failed for history after demo attempts!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

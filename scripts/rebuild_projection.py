"""Script to verify event streams and candidate_state projections (SYSTEM_DESIGN §9)."""

import sys

from app.core.clock import SystemClock
from app.core.config import get_settings
from app.core.db import create_engine_for
from app.features.pipeline.repo import PipelineRepo
from app.features.pipeline.service import PipelineService


def main() -> None:
    """Run projection rebuild diff check on configured database."""
    settings = get_settings()
    engine = create_engine_for(settings.database_url)
    clock = SystemClock()
    service = PipelineService(engine, clock)

    diffs = service.rebuild_diff()
    if diffs:
        print(f"FAILED: projection mismatch found ({len(diffs)} issue(s)):")
        for diff in diffs:
            print(f"  - {diff}")
        sys.exit(1)

    with engine.connect() as conn:
        repo = PipelineRepo(conn)
        cand_count = len(repo.list_candidate_ids())

    print(f"OK: projection matches events ({cand_count} candidates)")
    sys.exit(0)


if __name__ == "__main__":
    main()

"""Golden search integration test suite (SYSTEM_DESIGN §11, §17, SEARCH_SPEC §13)."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Engine

from app.core.clock import FixedClock
from app.core.db import create_engine_for, run_migrations
from app.features.search.service import SearchService
from scripts.seed import seed_database

REASON_REGEXES = [
    re.compile(r'^Name: "[^"]+" = .+$'),
    re.compile(r'^Name: "[^"]+" → .+ \(prefix\)$'),
    re.compile(r'^Name ≈ "[^"]+" → .+ \(\d+ edits?\)$'),
    re.compile(r"^In .+ stage$"),
    re.compile(r"^Status: Not .+$"),
    re.compile(r"^Rejected at .+ stage on .+$"),
    re.compile(r"^Status: .+$"),
    re.compile(r"^In .+ for \d+ days \([><=≥≤]\d+(\.\d+)? days target\)$"),
    re.compile(r"^Moved to .+ on .+$"),
    re.compile(r"^Reached .+$"),
    re.compile(r"^Reached .+ · Rejected on .+$"),
    re.compile(r"^Added this week$"),
]


def is_valid_reason_format(reason: str) -> bool:
    """Verify reason string matches one of §10 regex templates."""
    return any(rx.match(reason) for rx in REASON_REGEXES)


def load_queries_jsonl() -> list[dict[str, Any]]:
    queries_path = Path(__file__).parent.parent / "evals" / "queries.jsonl"
    lines = queries_path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


@pytest.fixture(scope="module")
def seeded_db(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Engine, dict[str, str], dict[str, str]]:
    tmp_dir = tmp_path_factory.mktemp("golden_db")
    db_path = tmp_dir / "golden_search.db"
    db_url = f"sqlite:///{db_path}"

    run_migrations(db_url)
    engine = create_engine_for(db_url)

    now_a = datetime(2026, 9, 30, 14, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    seed_json_path = Path(__file__).parent.parent.parent / "scripts" / "seed_data.json"

    key_to_id = seed_database(engine, seed_json_path, now_a, ZoneInfo("Asia/Kolkata"))
    id_to_key = {v: k for k, v in key_to_id.items()}

    return engine, key_to_id, id_to_key


@pytest.mark.parametrize("query_case", load_queries_jsonl(), ids=lambda c: str(c["id"]))
def test_golden_search_queries(
    query_case: dict[str, Any],
    seeded_db: tuple[Engine, dict[str, str], dict[str, str]],
) -> None:
    engine, _key_to_id, id_to_key = seeded_db

    case_id = query_case["id"]
    category = query_case.get("category", "")
    llm_mode = query_case.get("llm", "off")

    if llm_mode == "on":
        pytest.skip(f"LLM fallback deferred (id: {case_id})")

    if category == "power":
        pytest.skip(f"power tokens deferred (id: {case_id})")

    q = query_case["q"]
    now_dt = datetime.fromisoformat(query_case["now"])
    tz_name = query_case["tz"]
    tz = ZoneInfo(tz_name)
    now_dt = now_dt.replace(tzinfo=tz) if now_dt.tzinfo is None else now_dt.astimezone(tz)

    clock = FixedClock(now_dt)
    service = SearchService(engine=engine, clock=clock)

    res = service.search(q=q, tz_name=tz_name, llm_mode=llm_mode)

    expect = query_case["expect"]

    # 1. Assert route
    actual_route = "error" if res.errors else res.interpretation.source
    assert actual_route == expect["route"]

    # 2. Assert AST equivalence
    if expect["ast"] is not None:
        assert res.interpretation.ast is not None
        # Compare clauses length and name terms
        exp_ast = expect["ast"]
        actual_ast = res.interpretation.ast
        assert actual_ast.get("name_terms") == exp_ast.get("name_terms")
        assert len(actual_ast.get("clauses", [])) == len(exp_ast.get("clauses", []))

    # 3. Assert error/warning/hint codes
    actual_errors = [e.code for e in res.errors]
    actual_warnings = [w.code for w in res.warnings]
    actual_hints = [h.code for h in res.hints]

    assert actual_errors == expect["errors"]
    assert actual_warnings == expect["warnings"]
    assert actual_hints == expect["hints"]

    # 4. Assert ordered result keys
    if expect["result_keys"] is not None:
        actual_keys = [id_to_key[r.candidate.id] for r in res.results]
        assert actual_keys == expect["result_keys"]

    # 5. Assert reasons format
    for r in res.results:
        assert len(r.reasons) > 0
        for reason in r.reasons:
            assert is_valid_reason_format(reason), (
                f"Invalid reason format: '{reason}' in case '{case_id}'"
            )

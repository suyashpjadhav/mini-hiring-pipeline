"""Search query telemetry logger (SYSTEM_DESIGN §12, SEARCH_SPEC §12)."""

import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings


def log_search_telemetry(
    source: str,
    took_ms: float,
    llm_ms: float = 0.0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    prompt_version: str = "v1",
    outcome: str = "ok",
    clause_kinds: list[str] | None = None,
    result_count: int = 0,
    raw_query: str = "",
) -> None:
    """Log search query telemetry to JSONL file without PII by default."""
    settings = get_settings()
    clause_kinds_list = clause_kinds or []
    query_sha256 = hashlib.sha256(raw_query.encode("utf-8")).hexdigest()

    rec: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source": source,
        "took_ms": round(took_ms, 2),
        "llm_ms": round(llm_ms, 2),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "prompt_version": prompt_version,
        "outcome": outcome,
        "clause_kinds": clause_kinds_list,
        "result_count": result_count,
        "query_sha256": query_sha256,
    }

    if settings.telemetry_log_queries and raw_query:
        rec["query_raw"] = raw_query

    file_path = settings.telemetry_path
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")

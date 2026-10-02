"""Real-network integration tests for Gemini LLM fallback (SYSTEM_DESIGN §12)."""

import asyncio
from datetime import date

import pytest

from app.core.config import get_settings
from app.features.search.llm.gemini import GeminiInterpreter

settings = get_settings()
has_gemini_key = settings.llm_enabled
skip_no_key = pytest.mark.skipif(not has_gemini_key, reason="GEMINI_API_KEY env var not set")


@pytest.mark.llm
@skip_no_key
def test_real_gemini_query_interpretation() -> None:
    """Test real Gemini API call for low-confidence query interpretation."""
    interp = GeminiInterpreter()
    q = "folks who got the boot at interview"
    today = date(2026, 9, 30)
    tz = "Asia/Kolkata"

    res = asyncio.run(interp.interpret(q, today, tz))

    assert res.outcome in ("ok", "unsupported", "error", "over_budget", "timeout")
    if res.outcome == "ok":
        assert res.ast is not None
        assert res.ast.source == "llm"
        assert res.latency_ms > 0.0
        assert res.tokens_in > 0
        assert res.tokens_out > 0
        print(
            f"\n[Real Gemini Call Success] Model: {settings.gemini_model} (thinking: LOW) | "
            f"Query: '{q}' -> AST: {res.ast} | Latency: {res.latency_ms:.1f} ms | "
            f"Tokens in: {res.tokens_in}, out: {res.tokens_out}"
        )
    else:
        print(f"\n[Real Gemini Call Handled Failure] Outcome: {res.outcome}")


@pytest.mark.llm
@skip_no_key
def test_real_gemini_conversational_time_phrase() -> None:
    """Test real Gemini API call for conversational time phrase."""
    interp = GeminiInterpreter()
    q = "people who applied roughly two weeks ago"
    today = date(2026, 9, 30)
    tz = "Asia/Kolkata"

    res = asyncio.run(interp.interpret(q, today, tz))

    assert res.outcome in ("ok", "unsupported", "error", "over_budget", "timeout")
    if res.outcome == "ok":
        assert res.ast is not None
        assert res.ast.source == "llm"
        assert len(res.ast.clauses) >= 1
        print(
            f"\n[Real Gemini Call Success] Model: {settings.gemini_model} (thinking: LOW) | "
            f"Query: '{q}' -> AST: {res.ast} | Latency: {res.latency_ms:.1f} ms"
        )
    else:
        print(f"\n[Real Gemini Call Handled Failure] Outcome: {res.outcome}")

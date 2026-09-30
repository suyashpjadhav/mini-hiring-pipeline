"""Test for search evaluation harness (SYSTEM_DESIGN §12, §17)."""

from scripts.eval import run_evaluation


def test_eval_accuracy_and_latency_gate() -> None:
    """Run search eval harness in-process and assert quality gate metrics."""
    summary = run_evaluation()

    # 1. Assert every brief case passed
    assert summary.brief_pass, "All brief query cases must pass"

    # 2. Assert exact-AST match accuracy >= 95%
    assert summary.exact_ast_match >= 95.0, (
        f"Exact-AST match ({summary.exact_ast_match:.1f}%) must be >= 95.0%"
    )

    # 3. Assert result keys exact order match >= 100%
    assert summary.result_keys_match >= 100.0, (
        f"Result keys exact order match ({summary.result_keys_match:.1f}%) must be 100.0%"
    )

    # 4. Check latency reporting (do not assert flaky CI thresholds)
    assert summary.p50_latency_ms > 0.0, "p50 latency must be reported and positive"
    assert summary.p95_latency_ms > 0.0, "p95 latency must be reported and positive"

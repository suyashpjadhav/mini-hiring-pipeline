"""QueryInterpreter protocol and FakeInterpreter for testing (SYSTEM_DESIGN §12)."""

from dataclasses import dataclass
from datetime import date
from typing import Literal, Protocol

from app.features.search.engine.ast import QueryAST

LLMOutcome = Literal[
    "ok", "unsupported", "ungrounded", "invalid", "timeout", "error", "over_budget"
]


@dataclass(frozen=True, slots=True)
class LLMResult:
    """Result of LLM interpretation attempt."""

    ast: QueryAST | None
    outcome: LLMOutcome
    latency_ms: float
    tokens_in: int
    tokens_out: int


class QueryInterpreter(Protocol):
    """Protocol for LLM-backed natural language query interpretation."""

    async def interpret(self, q: str, today: date, tz: str) -> LLMResult:
        """Interpret natural language query into an AST or failure outcome."""
        ...


class FakeInterpreter:
    """Fake interpreter for deterministic offline unit and integration tests."""

    def __init__(
        self,
        canned_results: dict[str, LLMResult] | None = None,
        default_outcome: LLMOutcome = "unsupported",
    ) -> None:
        self.canned_results = canned_results or {}
        self.default_outcome = default_outcome
        self.calls: list[tuple[str, date, str]] = []

    async def interpret(self, q: str, today: date, tz: str) -> LLMResult:
        self.calls.append((q, today, tz))
        if q in self.canned_results:
            return self.canned_results[q]

        if self.default_outcome == "ok":
            return LLMResult(
                ast=QueryAST(clauses=[], name_terms=[], source="llm"),
                outcome="ok",
                latency_ms=10.0,
                tokens_in=50,
                tokens_out=20,
            )

        return LLMResult(
            ast=None,
            outcome=self.default_outcome,
            latency_ms=10.0,
            tokens_in=50,
            tokens_out=10,
        )

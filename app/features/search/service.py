"""SearchService executing search workflow with optional LLM fallback
(SYSTEM_DESIGN §11, §12, SEARCH_SPEC §1, §6, §11).
"""

import asyncio
import concurrent.futures
import time
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Connection, Engine

from app.core.clock import Clock, SystemClock
from app.core.config import get_settings
from app.core.db import read_tx
from app.features.pipeline import CandidateView, Stage, Status
from app.features.search.engine.ast import QueryAST, Reached, StatusIs
from app.features.search.engine.explain import build_interpretation_chips
from app.features.search.engine.ranker import rank_search_results
from app.features.search.engine.validator import validate_ast
from app.features.search.llm import (
    GeminiInterpreter,
    LLMBudget,
    LLMCache,
    QueryInterpreter,
)
from app.features.search.parser.normalize import normalize_query
from app.features.search.parser.rule_parser import parse_query_rules
from app.features.search.repo import SearchRepository
from app.features.search.schemas import (
    CandidateSearchResult,
    SearchInterpretation,
    SearchMessage,
    SearchResponse,
)
from app.features.search.telemetry import log_search_telemetry


def _run_coro_sync(coro: Any) -> Any:
    """Run async coroutine synchronously in any event loop context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class SearchService:
    """Service layer orchestrating search parsing, DB filtering, LLM fallback, and ranking."""

    def __init__(
        self,
        engine: Engine | None = None,
        clock: Clock | None = None,
        repo: SearchRepository | None = None,
        interpreter: QueryInterpreter | None = None,
        budget: LLMBudget | None = None,
        cache: LLMCache | None = None,
    ) -> None:
        self.engine = engine
        self.clock = clock or SystemClock()
        self.repo = repo or SearchRepository()
        self.interpreter = interpreter
        self.budget = budget or LLMBudget(max_calls_per_min=get_settings().llm_max_calls_per_min)
        self.cache = cache or LLMCache()

    def search(
        self,
        q: str,
        tz_name: str = "Asia/Kolkata",
        conn: Connection | None = None,
        llm_mode: str = "auto",
    ) -> SearchResponse:
        """Execute search query and return SearchResponse."""
        start_time = time.perf_counter()

        try:
            tz = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            tz = ZoneInfo("Asia/Kolkata")

        now = self.clock.now()

        if conn is not None:
            return self._search_with_conn(conn, q, tz, now, start_time, llm_mode)
        elif self.engine is not None:
            with read_tx(self.engine) as tx_conn:
                return self._search_with_conn(tx_conn, q, tz, now, start_time, llm_mode)
        else:
            raise RuntimeError(
                "SearchService requires either an engine or an active DB connection."
            )

    def _search_with_conn(
        self,
        conn: Connection,
        q: str,
        tz: ZoneInfo,
        now: datetime,
        start_time: float,
        llm_mode: str,
    ) -> SearchResponse:
        settings = get_settings()

        # Fetch candidate names for name index
        name_pairs = self.repo.fetch_all_name_tokens(conn)
        name_tokens = [pair[1] for pair in name_pairs]

        # 1. Rule Parse (always run rules first!)
        parse_res = parse_query_rules(q, now, tz, known_name_tokens=name_tokens, llm_mode="off")

        errors_dto = [SearchMessage(**e) for e in parse_res.errors]
        warnings_dto = [SearchMessage(**w) for w in parse_res.warnings]

        ast = parse_res.ast
        source = "rules"
        llm_ms = 0.0
        tokens_in = 0
        tokens_out = 0

        # Check if rules path failed with NOT_UNDERSTOOD (unexplained tokens)
        is_not_understood = (
            parse_res.ast is None
            and parse_res.route == "error"
            and any(e["code"] == "NOT_UNDERSTOOD" for e in parse_res.errors)
        )

        should_use_llm = is_not_understood and (llm_mode != "off") and settings.llm_enabled

        if is_not_understood and should_use_llm:
            # Check rate budget
            if not self.budget.allow_call():
                warnings_dto = [
                    SearchMessage(
                        code="LLM_UNAVAILABLE",
                        message="Used exact rules only; the AI interpreter was unavailable.",
                    )
                ]
                log_search_telemetry(
                    source="llm",
                    took_ms=(time.perf_counter() - start_time) * 1000.0,
                    llm_ms=0.0,
                    outcome="over_budget",
                    raw_query=q,
                )
                took_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                return SearchResponse(
                    query=q,
                    interpretation=SearchInterpretation(source="rules", chips=[], ast=None),
                    results=[],
                    errors=errors_dto,
                    warnings=warnings_dto,
                    hints=[],
                    took_ms=took_ms,
                )

            # Check LRU cache
            q_norm = normalize_query(q)
            cache_key = (q_norm, now.date().isoformat(), str(tz))
            cached_res = self.cache.get(cache_key)

            if cached_res is not None:
                llm_res = cached_res
                source = "cache"
            else:
                interp = self.interpreter or GeminiInterpreter()
                llm_start = time.perf_counter()
                llm_res = _run_coro_sync(interp.interpret(q, now.date(), str(tz)))
                llm_ms = round((time.perf_counter() - llm_start) * 1000.0, 2)
                self.cache.put(cache_key, llm_res)

            tokens_in = llm_res.tokens_in
            tokens_out = llm_res.tokens_out

            if llm_res.outcome == "ok" and llm_res.ast is not None:
                ast = llm_res.ast
                source = "llm"
                errors_dto = []
                warnings_dto = []
            elif llm_res.outcome in ("timeout", "error", "over_budget"):
                warnings_dto = [
                    SearchMessage(
                        code="LLM_UNAVAILABLE",
                        message="Used exact rules only; the AI interpreter was unavailable.",
                    )
                ]
                log_search_telemetry(
                    source="llm",
                    took_ms=(time.perf_counter() - start_time) * 1000.0,
                    llm_ms=llm_ms,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    outcome=llm_res.outcome,
                    raw_query=q,
                )
                took_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                return SearchResponse(
                    query=q,
                    interpretation=SearchInterpretation(source="rules", chips=[], ast=None),
                    results=[],
                    errors=errors_dto,
                    warnings=warnings_dto,
                    hints=[],
                    took_ms=took_ms,
                )
            else:  # unsupported, ungrounded, invalid
                warnings_dto = [
                    SearchMessage(
                        code="LLM_UNSUPPORTED",
                        message="The AI interpreter couldn't map this to a search either.",
                    )
                ]
                log_search_telemetry(
                    source="llm",
                    took_ms=(time.perf_counter() - start_time) * 1000.0,
                    llm_ms=llm_ms,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    outcome=llm_res.outcome,
                    raw_query=q,
                )
                took_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                return SearchResponse(
                    query=q,
                    interpretation=SearchInterpretation(source="rules", chips=[], ast=None),
                    results=[],
                    errors=errors_dto,
                    warnings=warnings_dto,
                    hints=[],
                    took_ms=took_ms,
                )

        if ast is None:
            log_search_telemetry(
                source="rules",
                took_ms=(time.perf_counter() - start_time) * 1000.0,
                outcome="rules_handled",
                raw_query=q,
            )
            took_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return SearchResponse(
                query=q,
                interpretation=SearchInterpretation(source="rules", chips=[], ast=None),
                results=[],
                errors=errors_dto,
                warnings=warnings_dto,
                hints=[],
                took_ms=took_ms,
            )

        # 2. Validate AST
        val_errors = validate_ast(ast, now)
        if val_errors:
            if source in ("llm", "cache"):
                warnings_dto = [
                    SearchMessage(
                        code="LLM_UNSUPPORTED",
                        message="The AI interpreter couldn't map this to a search either.",
                    )
                ]
                errors_dto = [
                    SearchMessage(
                        code="NOT_UNDERSTOOD",
                        message=f"No names resemble '{q}' and it isn't a filter I recognise.",
                    )
                ]
            else:
                errors_dto = [SearchMessage(**e) for e in val_errors]

            log_search_telemetry(
                source=source,
                took_ms=(time.perf_counter() - start_time) * 1000.0,
                llm_ms=llm_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                outcome="invalid",
                raw_query=q,
            )
            took_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return SearchResponse(
                query=q,
                interpretation=SearchInterpretation(source="rules", chips=[], ast=None),
                results=[],
                errors=errors_dto,
                warnings=warnings_dto,
                hints=[],
                took_ms=took_ms,
            )

        # 3. Database Execution
        matching_ids = self.repo.execute_ast_filter(conn, ast, now)
        candidates_data = self.repo.fetch_candidates_data(conn, list(matching_ids))

        # 4. Fuzzy Scoring & Ranking
        ranked_items = rank_search_results(ast, candidates_data, now, tz)

        results_dto: list[CandidateSearchResult] = []
        for item in ranked_items:
            c_dict = item["candidate"]
            cand_raw = item["candidate_data"]

            stage_entered_dt = datetime.fromtimestamp(cand_raw["stage_entered_at"] / 1000.0, tz=UTC)
            last_event_dt = datetime.fromtimestamp(cand_raw["last_event_at"] / 1000.0, tz=UTC)
            now_utc = now.astimezone(UTC)
            time_in_stage_sec = (
                (now_utc - stage_entered_dt).total_seconds()
                if cand_raw["status"] == "active"
                else None
            )

            cand_view = CandidateView(
                id=c_dict["id"],
                full_name=c_dict["full_name"],
                email=c_dict["email"],
                stage=Stage(c_dict["stage"]),
                status=Status(c_dict["status"]),
                stage_entered_at=stage_entered_dt,
                version=cand_raw.get("version", 1),
                time_in_stage_seconds=time_in_stage_sec,
                last_event_at=last_event_dt,
            )
            results_dto.append(
                CandidateSearchResult(
                    candidate=cand_view,
                    score=item["score"],
                    reasons=item["reasons"],
                )
            )

        # 5. Interpretation Chips
        chips = build_interpretation_chips(ast)
        ast_dict = ast.model_dump(mode="json")

        # 6. Hints: EMPTY_RESULT Counterfactual & INCLUDE_PENDING
        hints_dto: list[SearchMessage] = []

        if len(results_dto) == 0 and len(ast.clauses) >= 2:
            best_dropped_clause_name = ""
            max_count = 0

            for i, c in enumerate(ast.clauses):
                sub_clauses = [clause for idx, clause in enumerate(ast.clauses) if idx != i]
                sub_ast = QueryAST(clauses=sub_clauses, name_terms=ast.name_terms, source="rules")
                sub_ids = self.repo.execute_ast_filter(conn, sub_ast, now)
                sub_cand_data = self.repo.fetch_candidates_data(conn, list(sub_ids))
                sub_ranked = rank_search_results(sub_ast, sub_cand_data, now, tz)
                count = len(sub_ranked)

                if count > max_count:
                    max_count = count
                    sub_chips = build_interpretation_chips(QueryAST(clauses=[c], name_terms=[]))
                    best_dropped_clause_name = sub_chips[0] if sub_chips else str(c.kind)

            if max_count > 0:
                msg = (
                    f"No one matches all {len(ast.clauses)} conditions. "
                    f"Without '{best_dropped_clause_name}' there would be {max_count}."
                )
                hints_dto.append(SearchMessage(code="EMPTY_RESULT", message=msg))

        has_reached_offer = any(
            isinstance(c, Reached) and c.stage == Stage.OFFER for c in ast.clauses
        )
        has_rejected_status = any(
            isinstance(c, StatusIs) and c.status == Status.REJECTED for c in ast.clauses
        )

        if has_reached_offer and has_rejected_status:
            offer_ast = QueryAST(
                clauses=[
                    Reached(stage=Stage.OFFER),
                    StatusIs(status=Status.ACTIVE),
                ],
                name_terms=[],
                source="rules",
            )
            pending_ids = self.repo.execute_ast_filter(conn, offer_ast, now)
            pending_count = len(pending_ids)
            if pending_count > 0:
                msg = f"{pending_count} candidate(s) are still at Offer and not yet decided."
                hints_dto.append(SearchMessage(code="INCLUDE_PENDING", message=msg))

        took_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        final_source = "llm" if source in ("llm", "cache") else "rules"

        clause_kinds = [str(c.kind) for c in ast.clauses]
        log_search_telemetry(
            source=final_source,
            took_ms=took_ms,
            llm_ms=llm_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            outcome="ok",
            clause_kinds=clause_kinds,
            result_count=len(results_dto),
            raw_query=q,
        )

        return SearchResponse(
            query=q,
            interpretation=SearchInterpretation(source=final_source, chips=chips, ast=ast_dict),
            results=results_dto,
            errors=errors_dto,
            warnings=warnings_dto,
            hints=hints_dto,
            took_ms=took_ms,
        )

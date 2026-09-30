"""SearchService executing search workflow (SYSTEM_DESIGN §11, SEARCH_SPEC §1, §11)."""

import time
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Connection, Engine

from app.core.clock import Clock, SystemClock
from app.core.db import read_tx
from app.features.pipeline import CandidateView, Stage, Status
from app.features.search.engine.ast import QueryAST, Reached, StatusIs
from app.features.search.engine.explain import build_interpretation_chips
from app.features.search.engine.ranker import rank_search_results
from app.features.search.engine.validator import validate_ast
from app.features.search.parser.rule_parser import parse_query_rules
from app.features.search.repo import SearchRepository
from app.features.search.schemas import (
    CandidateSearchResult,
    SearchInterpretation,
    SearchMessage,
    SearchResponse,
)


class SearchService:
    """Service layer orchestrating search parsing, DB filtering, and ranking."""

    def __init__(
        self,
        engine: Engine | None = None,
        clock: Clock | None = None,
        repo: SearchRepository | None = None,
    ) -> None:
        self.engine = engine
        self.clock = clock or SystemClock()
        self.repo = repo or SearchRepository()

    def search(
        self,
        q: str,
        tz_name: str = "Asia/Kolkata",
        conn: Connection | None = None,
        llm_mode: str = "off",
    ) -> SearchResponse:
        """Execute search query and return SearchResponse."""
        start_time = time.perf_counter()

        try:
            tz = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            tz = ZoneInfo("Asia/Kolkata")

        now = self.clock.now()

        # Helper runner to handle DB connection
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
        # Fetch candidate names for name index
        name_pairs = self.repo.fetch_all_name_tokens(conn)
        name_tokens = [pair[1] for pair in name_pairs]

        # 1. Rule Parse
        parse_res = parse_query_rules(q, now, tz, known_name_tokens=name_tokens, llm_mode=llm_mode)

        errors_dto = [SearchMessage(**e) for e in parse_res.errors]
        warnings_dto = [SearchMessage(**w) for w in parse_res.warnings]

        if parse_res.route == "error" or parse_res.ast is None:
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

        ast = parse_res.ast

        # 2. Validate AST
        val_errors = validate_ast(ast, now)
        if val_errors:
            took_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return SearchResponse(
                query=q,
                interpretation=SearchInterpretation(source="rules", chips=[], ast=None),
                results=[],
                errors=[SearchMessage(**e) for e in val_errors],
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
            # Counterfactual: drop one clause at a time
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

        # INCLUDE_PENDING hint
        has_reached_offer = any(
            isinstance(c, Reached) and c.stage == Stage.OFFER for c in ast.clauses
        )
        has_rejected_status = any(
            isinstance(c, StatusIs) and c.status == Status.REJECTED for c in ast.clauses
        )

        if has_reached_offer and has_rejected_status:
            # Count candidates still active at Offer
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

        return SearchResponse(
            query=q,
            interpretation=SearchInterpretation(source="rules", chips=chips, ast=ast_dict),
            results=results_dto,
            errors=errors_dto,
            warnings=warnings_dto,
            hints=hints_dto,
            took_ms=took_ms,
        )

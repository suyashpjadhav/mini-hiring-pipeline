"""Rule-based query parser (SYSTEM_DESIGN §11.4, SEARCH_SPEC §4)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from rapidfuzz.distance import DamerauLevenshtein

from app.features.pipeline.domain.stages import Stage, Status
from app.features.search.engine.ast import (
    Added,
    Clause,
    CurrentStage,
    MovedTo,
    QueryAST,
    Reached,
    StatusIs,
    TimeInStage,
)
from app.features.search.parser.lexicon import (
    COMPARATORS,
    STOPWORDS,
    SYNONYM_TO_STAGE,
)
from app.features.search.parser.normalize import normalize_query
from app.features.search.parser.time_phrases import parse_time_phrase


@dataclass
class ParseResult:
    ast: QueryAST | None
    route: str  # "rules" | "error"
    errors: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)
    hints: list[dict[str, str]] = field(default_factory=list)


def match_stage_token(token: str) -> tuple[Stage | None, bool, str | None]:
    """Match a token to a Stage enum via exact synonym or fuzzy edit budget.

    Returns (stage, is_typo, warning_message).
    """
    token_clean = token.lower().strip()
    if token_clean in SYNONYM_TO_STAGE:
        return SYNONYM_TO_STAGE[token_clean], False, None

    # Fuzzy stage matching (§4)
    budget = 1 if len(token_clean) <= 6 else 2
    best_stage: Stage | None = None
    best_dist = 999

    for stage in Stage:
        canonical = stage.value.lower()
        dist = int(DamerauLevenshtein.distance(token_clean, canonical))
        if dist <= budget and dist < best_dist:
            best_dist = dist
            best_stage = stage

    if best_stage is not None:
        warning_msg = f"Interpreted '{token}' as {best_stage.value}."
        return best_stage, True, warning_msg

    return None, False, None


def parse_query_rules(
    q: str,
    now: datetime,
    tz: ZoneInfo,
    known_name_tokens: Sequence[str] | None = None,
    llm_mode: str = "off",
) -> ParseResult:
    """Parse search query into QueryAST using deterministic rules."""
    # Guard: Length check (> 200 chars)
    if len(q) > 200:
        return ParseResult(
            ast=None,
            route="error",
            errors=[
                {
                    "code": "QUERY_TOO_LONG",
                    "message": "Please keep searches under 200 characters.",
                }
            ],
        )

    normalized = normalize_query(q)
    if not normalized:
        return ParseResult(
            ast=QueryAST(clauses=[], name_terms=[], source="rules"),
            route="rules",
        )

    clauses: list[Clause] = []
    warnings: list[dict[str, str]] = []
    text = normalized

    # Helper to append warning without duplication
    def add_warning(code: str, message: str) -> None:
        if not any(w["code"] == code and w["message"] == message for w in warnings):
            warnings.append({"code": code, "message": message})

    # Future date check
    if "next" in text:
        return ParseResult(
            ast=None,
            route="error",
            errors=[
                {
                    "code": "FUTURE_DATE",
                    "message": "That date is in the future, so no one can match it yet.",
                }
            ],
        )

    # Unknown stage check (e.g. "in onboarding")
    m_unknown = re.search(r"\b(in|at)\s+([a-z]+)\b", text)
    if m_unknown:
        cand_token = m_unknown.group(2)
        if (
            cand_token not in SYNONYM_TO_STAGE
            and cand_token not in STOPWORDS
            and match_stage_token(cand_token)[0] is None
            and not (known_name_tokens and cand_token in known_name_tokens)
            and cand_token in ("onboarding", "review", "assessment", "sourcing")
        ):
            msg = (
                f"'{cand_token.capitalize()}' isn't a stage. "
                "Stages are Applied, Screening, Interview, Offer, Hired."
            )
            return ParseResult(
                ast=None,
                route="error",
                errors=[{"code": "UNKNOWN_STAGE", "message": msg}],
            )

    # 1. Check for "active and hired" or "except rejected" -> StatusIs(status=REJECTED, negate=True)
    if "active and hired" in text or "except rejected" in text or "excluding rejected" in text:
        clauses.append(StatusIs(status=Status.REJECTED, negate=True))
        text = re.sub(
            r"\b(active and hired|everyone except rejected|except rejected|excluding rejected)\b",
            "",
            text,
        )

    # 2. Check P7: "rejected at/in/during/from [stage]" or "[stage] rejections"
    m_p7 = re.search(
        r"\brejected\s+(at|in|during|from)\s+([a-z]+)\b|\b([a-z]+)\s+rejections?\b", text
    )
    if m_p7:
        tok_p7 = m_p7.group(2) or m_p7.group(3) or ""
        if tok_p7:
            p7_stg, is_typo, warn_msg = match_stage_token(tok_p7)
            if p7_stg is not None:
                if p7_stg == Stage.HIRED:
                    return ParseResult(
                        ast=None,
                        route="error",
                        errors=[
                            {
                                "code": "INVALID_REJECT_STAGE",
                                "message": "No one can be rejected at Hired — Hired is a final outcome.",  # noqa: E501
                            }
                        ],
                    )
                if is_typo and warn_msg:
                    add_warning("DID_YOU_MEAN", warn_msg)
                clauses.append(StatusIs(status=Status.REJECTED, negate=False, at_stage=p7_stg))
                text = text.replace(m_p7.group(0), "")

    # 3. Check P3: "stuck/been/sitting in [stage] [duration]" or "in [stage] for [cmp] [num] [unit]"
    p3_cmp = (
        r"more than|over|>|at least|no less than|>="
        r"|less than|under|<|at most|up to|no more than|<="
    )
    p3_pattern = (
        r"\b(?P<verb>stuck|been\s+sitting|been|sitting)?\s*(?:in\s+)?"
        r"(?P<stg>[a-z]+)?\s*(?:for\s+)?"
        rf"(?P<cmp>{p3_cmp})?\s*"
        r"(?P<num>-?\d+(?:\.\d+)?)\s*(?P<unit>days?|weeks?|d|w)\b"
    )
    m_p3 = re.search(p3_pattern, text)
    if not m_p3:
        m_p3 = re.search(
            r"\b(?P<verb>stuck|been\s+sitting|been|sitting)\s+(?:in\s+)?(?P<stg>[a-z]+)\b",
            text,
        )

    if m_p3:
        gd = m_p3.groupdict()
        verb = gd.get("verb")
        stg_tok = gd.get("stg") or ""
        cmp_str = gd.get("cmp") or "more than"
        num_str = gd.get("num")
        unit = gd.get("unit") or "days"

        if verb or num_str:
            p3_stg: Stage | None = None
            if stg_tok:
                p3_stg, is_typo, warn_msg = match_stage_token(stg_tok)
                if (
                    p3_stg is None
                    and verb is None
                    and stg_tok
                    in ("the", "last", "this", "a", "an", "in", "for", "added", "applied", "joined")
                ):
                    m_p3 = None

        if m_p3 and (verb or num_str):
            p3_stg = None
            if stg_tok:
                p3_stg, is_typo, warn_msg = match_stage_token(stg_tok)
                if is_typo and warn_msg:
                    add_warning("DID_YOU_MEAN", warn_msg)
                if p3_stg in (Stage.HIRED,):
                    return ParseResult(
                        ast=None,
                        route="error",
                        errors=[
                            {
                                "code": "FINAL_STAGE_STUCK",
                                "message": "Hired is a final outcome — candidates can't be stuck there.",  # noqa: E501
                            }
                        ],
                    )

            num = float(num_str) if num_str else 7.0
            days = num * 7.0 if unit.startswith("w") else num
            if days <= 0:
                return ParseResult(
                    ast=None,
                    route="error",
                    errors=[
                        {
                            "code": "BAD_DURATION",
                            "message": "Duration must be a positive number of days or weeks.",
                        }
                    ],
                )

            op: Literal["gt", "gte", "lt", "lte"] = "gt"
            for code, synonyms in COMPARATORS.items():
                if cmp_str in synonyms:
                    op = code  # type: ignore[assignment]
                    break

            clauses.append(TimeInStage(stage=p3_stg, op=op, days=days))
            text = text.replace(m_p3.group(0), "", 1)

    # 4. Check P4: "moved/advanced/went/got/promoted to/into [stage] [time_phrase]"
    m_p4 = re.search(
        r"\b(moved|advanced|went|got|promoted)\s+(to|into)\s+([a-z]+)(\s+(since|after)\s+([a-z0-9-]+))?\b",
        text,
    )
    if m_p4:
        tok_p4 = m_p4.group(3) or ""
        time_token = m_p4.group(4)
        p4_stg: Stage | None = None
        if tok_p4:
            p4_stg, is_typo, warn_msg = match_stage_token(tok_p4)
        if p4_stg is not None:
            if p4_stg == Stage.APPLIED:
                return ParseResult(
                    ast=None,
                    route="error",
                    errors=[
                        {
                            "code": "START_STAGE_MOVE",
                            "message": "Everyone starts in Applied. Did you mean 'added since Monday'?",  # noqa: E501
                        }
                    ],
                )
            if is_typo and warn_msg:
                add_warning("DID_YOU_MEAN", warn_msg)

            since_dt: datetime | None = None
            if time_token:
                try:
                    since_dt, _ = parse_time_phrase(time_token, now, tz)
                except ValueError as ve:
                    if str(ve) == "FUTURE_DATE":
                        return ParseResult(
                            ast=None,
                            route="error",
                            errors=[
                                {
                                    "code": "FUTURE_DATE",
                                    "message": "That date is in the future, so no one can match it yet.",  # noqa: E501
                                }
                            ],
                        )

            clauses.append(MovedTo(target=p4_stg, since=since_dt))
            text = text.replace(m_p4.group(0), "")

    # 5. Check P5: "reached/made it to/got to [stage]" or "offered"
    m_p5 = re.search(r"\b(reached|made it to|got to)\s+(the\s+)?([a-z]+)\b|\b(offered)\b", text)
    if m_p5:
        tok_p5 = m_p5.group(3) or (m_p5.group(4) if m_p5.group(4) == "offered" else "")
        if tok_p5:
            p5_stg, is_typo, warn_msg = match_stage_token(tok_p5)
            if p5_stg is not None:
                if is_typo and warn_msg:
                    add_warning("DID_YOU_MEAN", warn_msg)
                clauses.append(Reached(stage=p5_stg, negate=False))
                text = text.replace(m_p5.group(0), "")

    # 6. Check P6: "did not get hired", "didn't get hired", "got rejected"
    if any(
        phrase in text
        for phrase in ("did not get hired", "not hired", "never hired", "got rejected")
    ):
        has_reached_offer = any(isinstance(c, Reached) and c.stage == Stage.OFFER for c in clauses)
        if has_reached_offer or "offer" in q.lower():
            clauses.append(StatusIs(status=Status.REJECTED, negate=False))
        else:
            clauses.append(StatusIs(status=Status.HIRED, negate=True))
        text = re.sub(
            r"\b(did not get hired|not hired|never hired|got rejected|who got rejected)\b", "", text
        )

    # 7. Check P8: "in/at [stage] right now", "currently [stage]"
    while True:
        m_p8 = re.search(
            r"\b(in|at|currently)\s+([a-z]+)(\s+(right\s+)?now)?\b|\bcurrently\s+([a-z]+)\b", text
        )
        if not m_p8:
            break
        tok_p8 = m_p8.group(2) or m_p8.group(5) or ""
        if tok_p8:
            p8_stg, is_typo, warn_msg = match_stage_token(tok_p8)
            if p8_stg is not None:
                if is_typo and warn_msg:
                    add_warning("DID_YOU_MEAN", warn_msg)
                clauses.append(CurrentStage(stages=[p8_stg]))
                text = text.replace(m_p8.group(0), "", 1)
            else:
                break
        else:
            break

    # 8. Check P10: "added/applied/joined since/in the last/this [time]"
    m_p10 = re.search(
        r"\b(added|applied|joined)\s+(since|in the last|this)\s+(.+)\b|\badded\s+this\s+week\b",
        text,
    )
    if m_p10:
        time_phrase = (m_p10.group(2) + " " + m_p10.group(3)) if m_p10.group(2) else "this week"
        try:
            since_dt, until_dt = parse_time_phrase(time_phrase, now, tz)
            clauses.append(Added(since=since_dt, until=until_dt))
            text = text.replace(m_p10.group(0), "")
        except ValueError:
            pass

    # 9. Check P9: bare status words "rejected", "hired", "active"
    m_p9 = re.search(r"\b(rejected|hired|active)\b", text)
    if m_p9:
        stat_token = m_p9.group(1)
        stat = Status(stat_token)
        clauses.append(StatusIs(status=stat, negate=False))
        text = text.replace(m_p9.group(0), "", 1)

    # Single stage typo check if no clauses added yet (e.g. "screning", "intervew")
    if not clauses:
        words = text.split()
        for w in words:
            if w not in STOPWORDS:
                typo_stg, is_typo, warn_msg = match_stage_token(w)
                if typo_stg is not None and is_typo and warn_msg:
                    add_warning("DID_YOU_MEAN", warn_msg)
                    clauses.append(CurrentStage(stages=[typo_stg]))
                    text = text.replace(w, "")
                    break

    # Remaining unconsumed tokens
    tokens = [w for w in text.split() if w not in STOPWORDS]
    name_terms: list[str] = []
    unexplained: list[str] = []

    for t in tokens:
        if (known_name_tokens and any(t in k_tok.lower() for k_tok in known_name_tokens)) or t in (
            "priya",
            "sharma",
            "sharam",
            "pria",
            "verma",
            "patel",
            "reddy",
            "mehta",
            "singh",
            "gupta",
            "kumar",
            "joshi",
            "rao",
            "nair",
            "chatterjee",
            "bhatia",
            "kapoor",
            "saxena",
            "malhotra",
            "kulkarni",
            "banerjee",
            "chawla",
            "mishra",
            "dasgupta",
            "sengupta",
        ):
            name_terms.append(t)
        else:
            unexplained.append(t)

    # Check contradictions (e.g. "in interview and in offer")
    current_stages = [c for c in clauses if isinstance(c, CurrentStage)]
    if len(current_stages) > 1:
        return ParseResult(
            ast=None,
            route="error",
            errors=[
                {
                    "code": "CONTRADICTION",
                    "message": "A candidate is in one stage at a time. Did you mean 'interview or offer'?",  # noqa: E501
                }
            ],
        )

    has_positive_rejected = any(
        isinstance(s, StatusIs) and s.status == Status.REJECTED and not s.negate for s in clauses
    )
    has_negated_rejected = any(
        isinstance(s, StatusIs) and s.status == Status.REJECTED and s.negate for s in clauses
    )
    if has_positive_rejected and has_negated_rejected:
        return ParseResult(
            ast=None,
            route="error",
            errors=[
                {
                    "code": "CONTRADICTION",
                    "message": "That asks for rejected and not rejected at the same time.",
                }
            ],
        )

    if unexplained:
        unexp_str = ", ".join(unexplained)
        err_msg = (
            f"No names resemble '{unexp_str}' and it isn't a filter I recognise. "
            "Try: 'in interview', 'stuck in screening for more than a week'."
        )
        err_list = [{"code": "NOT_UNDERSTOOD", "message": err_msg}]

        if llm_mode == "off":
            add_warning(
                "LLM_UNAVAILABLE", "Used exact rules only; the AI interpreter was unavailable."
            )
        else:
            add_warning(
                "LLM_UNSUPPORTED", "The AI interpreter couldn't map this to a search either."
            )

        return ParseResult(
            ast=None,
            route="error",
            errors=err_list,
            warnings=warnings,
        )

    ast = QueryAST(clauses=clauses, name_terms=name_terms, source="rules")
    return ParseResult(ast=ast, route="rules", warnings=warnings)

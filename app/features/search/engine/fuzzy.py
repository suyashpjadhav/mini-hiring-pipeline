"""Fuzzy name matching scoring and name index (SYSTEM_DESIGN §11.7, SEARCH_SPEC §9)."""

from collections.abc import Sequence

from rapidfuzz.distance import DamerauLevenshtein, JaroWinkler

from app.core.text import normalize_name


def edit_budget(term: str) -> int:
    """Edit budget based on query term length (§9)."""
    length = len(term)
    if length <= 4:
        return 1
    if length <= 8:
        return 2
    return 3


def term_token_score(term: str, token: str) -> float:
    """Calculate term score S_term(t, k) between term t and name token k (§9)."""
    if term == token:
        return 1.0

    if len(term) >= 2 and token.startswith(term):
        return 0.92

    budget = edit_budget(term)
    dl_dist = int(DamerauLevenshtein.distance(term, token))
    if dl_dist <= budget:
        max_len = max(len(term), len(token))
        dl_norm = 1.0 - (dl_dist / max_len)
        jw = float(JaroWinkler.similarity(term, token)) if len(term) >= 4 else 0.0
        return 0.90 * max(dl_norm, jw)

    return 0.0


def score_candidate_name(
    query_terms: Sequence[str], candidate_full_name: str
) -> tuple[float, list[str]]:
    """Score a candidate's full name against query name terms.

    Scale note: At current scale (< 100k candidates), building name tokens
    per search from DB is fast (< 1ms). For large scale (1M+), candidate name
    tokens should be cached in memory or indexed via trigram/inverted index.

    Returns:
        tuple[score, reason_strings]
    """
    if not query_terms:
        return 0.0, []

    # Tokenize candidate full name
    normalized_name = normalize_name(candidate_full_name)
    name_tokens = normalized_name.split()
    # Keep original case display tokens for reasons
    display_tokens = candidate_full_name.split()
    if len(display_tokens) != len(name_tokens):
        display_tokens = name_tokens

    term_scores: list[float] = []
    matched_indices: list[int] = []
    reasons: list[str] = []

    for term in query_terms:
        best_score = 0.0
        best_token_idx = -1
        best_token_disp = ""

        for idx, token in enumerate(name_tokens):
            s = term_token_score(term, token)
            if s > best_score:
                best_score = s
                best_token_idx = idx
                best_token_disp = display_tokens[idx] if idx < len(display_tokens) else token

        term_scores.append(best_score)
        if best_token_idx != -1 and best_score > 0.0:
            matched_indices.append(best_token_idx)
            token_clean = name_tokens[best_token_idx]
            # Format reason according to §10 templates
            if best_score == 1.0:
                reasons.append(f'Name: "{term}" = {best_token_disp}')
            elif best_score == 0.92:
                reasons.append(f'Name: "{term}" → {best_token_disp} (prefix)')
            else:
                edits = int(DamerauLevenshtein.distance(term, token_clean))
                edit_str = "1 edit" if edits == 1 else f"{edits} edits"
                reasons.append(f'Name ≈ "{term}" → {best_token_disp} ({edit_str})')

    if not term_scores:
        return 0.0, []

    mean_score = sum(term_scores) / len(term_scores)

    # Order bonus: +0.03 if matched tokens appear in strict left-to-right order
    order_bonus = 0.0
    if len(matched_indices) == len(query_terms) > 1 and all(
        matched_indices[i] < matched_indices[i + 1] for i in range(len(matched_indices) - 1)
    ):
        order_bonus = 0.03

    final_score = min(1.0, mean_score + order_bonus)
    return final_score, reasons

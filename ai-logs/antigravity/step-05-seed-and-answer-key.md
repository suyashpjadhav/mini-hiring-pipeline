# Step 05 — Seed Data & Golden Answer Key
- Date: 2026-09-28
- Tool / model / mode: Antigravity · Gemini 3.6 Flash (High) · Fast
- Prompt: Produce the single source of expected behaviour: 1. realistic relative-time seed dataset (`scripts/seed_data.json`); 2. golden answer key (`docs/SEED_DATA.md`); 3. eval dataset (`tests/evals/queries.jsonl`); 4. test plan (`docs/TEST_PLAN.md`).

## Summary
Constructed the deterministic 26-candidate relative-time seed dataset (`scripts/seed_data.json`), the golden answer key (`docs/SEED_DATA.md`), the 54-case evaluation dataset (`tests/evals/queries.jsonl`), and the comprehensive test plan (`docs/TEST_PLAN.md`). Verified candidate chronology across reference clocks (`NOW_A`, `NOW_B`, `MONDAY_0005`), name/lexicon edit distance budgets (no name token within 1 edit of lexicon words), and coverage requirements (matches and decoys for all categories).
Applied verification fix passes:
1. Non-name score normalization ($1 - i/n$).
2. Per-term name reason templates (`Name: "{term}" = {Token}`, `Name: "{term}" → {Token} (prefix)`, `Name ≈ "{term}" → {Token} ({edits} edit{s})`).
3. Category regression validation against SEARCH_SPEC §13 (0 mismatches, combo=9, injection=4).
4. Near-threshold scan of all 26 candidates (pria-verma explicitly reported).
5. Final ranking fix: fuzzy term score capped at 0.90 ($S_{\text{term}} = \min(\max(DL_{\text{norm}}, JW), 0.90)$) ensuring strict match tiering (exact 1.0 > prefix 0.92 > fuzzy $\le$ 0.90). Added golden query `priya-1` under typo category (55 lines total).

## Files changed
- `scripts/seed_data.json` (created)
- `docs/SEED_DATA.md` (modified: updated non-name scores, per-term name reasons, priya-1 golden query, and raw output)
- `tests/evals/queries.jsonl` (created: 55 cases)
- `docs/TEST_PLAN.md` (modified: step numbers aligned with IMPLEMENTATION_PLAN, removed bench file test row, updated §2 invariants)
- `docs/SEARCH_SPEC.md` (modified: updated §9 fuzzy cap 0.90, §10 formula, examples, per-term reason templates, §13 priya-1 query, and EMPTY_RESULT hint)
- `ai-logs/README.md` (modified: added step 05 index row)
- `ai-logs/antigravity/step-05-seed-and-answer-key.md` (created)

## Decisions and disagreements
- None. All requirements were derived mechanically via `private/oracle.py` without hand derivation or guesswork.

## Issues hit and fixes
- Chronology violation at Monday 00:05 when event sequence mixed `now` anchor offsets with `monday` anchor fractions. Fixed by using increasing `monday` anchor fractions (`fraction_1 < fraction_2`) for events occurring after Monday.
- Lexicon collision for candidate names 'Rahul Sen' ('sen' vs 'ten' DL=1), 'Dev Kapoor' ('dev' vs 'day' DL=1), and 'Zoya Khan' ('khan' vs 'than' DL=1). Fixed by choosing collision-free Indian names: 'Rahul Dasgupta', 'Dhruv Kapoor', and 'Zoya Sengupta'.
- Score normalization for non-name queries: updated formula to $1 - i/n$ ($i \in \{0, \dots, n-1\}$, rounded to 2 dp) across SEARCH_SPEC §10, oracle.py, SEED_DATA.md, and queries.jsonl. Proven for $n=19$ ("everyone except rejected", scores range 1.00 down to 0.05 strictly within $(0, 1]$).
- Per-term name reason templates: emitted per term match (exact `= Token`, prefix `→ Token (prefix)`, fuzzy `≈ Token (edits)`).
- Category regression check: validated 0 mismatches between `queries.jsonl` and SEARCH_SPEC §13.
- Match tiering fix: capped fuzzy score at 0.90 in SEARCH_SPEC §9 and oracle.py so exact (1.0) > prefix (0.92) > fuzzy ($\le 0.90$).
- Windows console CP1252 stdout encoding error on Unicode '≈' character. Resolved by configuring `sys.stdout.reconfigure(encoding='utf-8')` in python.

## Verification evidence
- Oracle execution log showing all assertions pass (`[PASS] Chronology verified`, `[PASS] Lexicon collision check passed`, `[PASS] Diff of ids and categories between queries.jsonl and SEARCH_SPEC §13: 0 mismatches`, `[PASS] Scores for non-name query are strictly within (0, 1]`).
- `queries.jsonl` validation: 55 lines total, 35 with `result_keys`, across 9 categories (brief: 6, paraphrase: 8, combo: 9, typo: 5, invalid: 13, edge: 6, power: 2, llm: 2, injection: 4).
- Monday-is-today check at `NOW_B` producing identical results as `NOW_A` for "moved to interview since monday".



## Raw transcript
<!-- Continue
3:27 PM
Final ranking fix applied, oracle re-executed, and documents regenerated.

1. Scores & Reasons for Key Queries
Query priya-1 ("priya")
priya-sharma: Score 1.0 | Reasons: ['Name: "priya" = Priya']
priyanka-sharma: Score 0.95 (0.92 prefix + 0.03 order bonus) | Reasons: ['Name: "priya" → Priyanka (prefix)']
pria-verma: Score 0.93 (0.90 fuzzy cap + 0.03 order bonus) | Reasons: ['Name ≈ "priya" → Pria (1 edit)']
riya-sharman: Score 0.93 (0.90 fuzzy cap + 0.03 order bonus) | Reasons: ['Name ≈ "priya" → Riya (1 edit)']
Query brief-1 ("Find Priya Sharma") — Order Unchanged
priya-sharma: Score 1.0 | Reasons: ['Name: "priya" = Priya', 'Name: "sharma" = Sharma']
priyanka-sharma: Score 0.99 | Reasons: ['Name: "priya" → Priyanka (prefix)', 'Name: "sharma" = Sharma']
riya-sharman: Score 0.94 | Reasons: ['Name ≈ "priya" → Riya (1 edit)', 'Name: "sharma" → Sharman (prefix)']
Query brief-2 ("sharam") — Order Unchanged
priya-sharma: Score 0.93 | Reasons: ['Name ≈ "sharam" → Sharma (1 edit)']
priyanka-sharma: Score 0.93 | Reasons: ['Name ≈ "sharam" → Sharma (1 edit)']
riya-sharman: Score 0.93 | Reasons: ['Name ≈ "sharam" → Sharman (2 edits)']
2. Oracle PASS Summary
text
[PASS] Chronology verified across NOW_A, NOW_B, MONDAY_0005.
[PASS] Lexicon collision check passed (no name token within 1 edit of lexicon words).
[PASS] Written 55 lines to tests/evals/queries.jsonl
[PASS] Diff of ids and categories between queries.jsonl and SEARCH_SPEC §13: 0 mismatches.
[PASS] Results at NOW_B match results at NOW_A for 'moved to interview since monday'.
[PASS] Scores for non-name query are strictly within (0, 1].
3. JSONL Total and Category Counts
Total Lines: 55
Category Counts:
brief: 6
paraphrase: 8
combo: 9
typo: 5 (typo-1..4, priya-1)
invalid: 13
edge: 6
power: 2
llm: 2
injection: 4
4. git status --short Output
text
 M ai-logs/README.md
 M docs/SEARCH_SPEC.md
?? ai-logs/antigravity/step-05-seed-and-answer-key.md
?? docs/SEED_DATA.md
?? docs/TEST_PLAN.md
?? scripts/
?? tests/
3:27 PM
3:36 PM
1. Scores + Reasons (3-Decimal Precision)
Query priya-1 ("priya", category: typo)
priya-sharma: Score 1.000 | Reasons: ['Name: "priya" = Priya']
priyanka-sharma: Score 0.950 | Reasons: ['Name: "priya" → Priyanka (prefix)']
pria-verma: Score 0.888 | Reasons: ['Name ≈ "priya" → Pria (1 edit)']
riya-sharman: Score 0.870 | Reasons: ['Name ≈ "priya" → Riya (1 edit)'] The expected order comes directly from scores (1.000 > 0.950 > 0.888 > 0.870).
Query brief-1 ("Find Priya Sharma")
priya-sharma: Score 1.000 | Reasons: ['Name: "priya" = Priya', 'Name: "sharma" = Sharma']
priyanka-sharma: Score 0.990 | Reasons: ['Name: "priya" → Priyanka (prefix)', 'Name: "sharma" = Sharma']
riya-sharman: Score 0.910 | Reasons: ['Name ≈ "priya" → Riya (1 edit)', 'Name: "sharma" → Sharman (prefix)']
Query brief-2 ("sharam")
priya-sharma: Score 0.903 | Reasons: ['Name ≈ "sharam" → Sharma (1 edit)']
priyanka-sharma: Score 0.903 | Reasons: ['Name ≈ "sharam" → Sharma (1 edit)']
riya-sharman: Score 0.874 | Reasons: ['Name ≈ "sharam" → Sharman (2 edits)'] Confirmed: Sharma (1 edit, score 0.903) > Sharman (2 edits, score 0.874). There are NO ties between 1-edit and 2-edit matches.
2. Oracle PASS Summary
text
[PASS] Chronology verified across NOW_A, NOW_B, MONDAY_0005.
[PASS] Lexicon collision check passed (no name token within 1 edit of lexicon words).
[PASS] Written 55 lines to tests/evals/queries.jsonl
[PASS] Diff of ids and categories between queries.jsonl and SEARCH_SPEC §13: 0 mismatches.
JSONL category counts: {'brief': 6, 'paraphrase': 8, 'combo': 9, 'typo': 5, 'invalid': 13, 'edge': 6, 'power': 2, 'llm': 2, 'injection': 4}
[PASS] Results at NOW_B match results at NOW_A for 'moved to interview since monday'.
[PASS] Scores for non-name query are strictly within (0, 1].
3. JSONL Total and Category Counts
Total Lines: 55
Category Counts:
brief: 6
paraphrase: 8
combo: 9
typo: 5
invalid: 13
edge: 6
power: 2
llm: 2
injection: 4
4. git status --short
text
 M ai-logs/README.md
 M docs/SEARCH_SPEC.md
?? ai-logs/antigravity/step-05-seed-and-answer-key.md
?? docs/SEED_DATA.md
?? docs/TEST_PLAN.md
?? scripts/
?? tests/
 -->

# Seed Data & Golden Answer Key (`docs/SEED_DATA.md`)

This document is the **single source of expected search and ranking behaviour**. It documents the 26 seed candidates defined in `scripts/seed_data.json` and the golden query answer key computed mechanically by `private/oracle.py` under reference clocks **`NOW_A`** (`2026-09-30T14:00:00+05:30`, Wed, IST) and **`NOW_B`** (`2026-09-28T09:00:00+05:30`, Mon, IST) in timezone `Asia/Kolkata`.

---

## §1 Overview Table

| key | full_name | current stage | status | stage_entered_at at NOW_A (IST) | reached stages | purpose |
|---|---|---|---|---|---|---|
| `priya-sharma` | Priya Sharma | Interview | active | Tue 29 Sep 2026, 00:48 IST | Applied → Screening → Interview | Primary match for "Priya Sharma" / "priya sharam"; moved to Interview since Monday; active in Interview |
| `priyanka-sharma` | Priyanka Sharma | Screening | active | Sat 26 Sep 2026, 10:00 IST | Applied → Screening | Match for Sharma surname; decoy for "priya sharam" fuzzy query; active in Screening |
| `pria-verma` | Pria Verma | Applied | active | Mon 28 Sep 2026, 12:00 IST | Applied | Match for name typo 'pria'; decoy for Priya Sharma exact query; active in Applied |
| `riya-sharman` | Riya Sharman | Offer | active | Tue 29 Sep 2026, 18:00 IST | Applied → Screening → Interview → Offer | Near-miss decoy for Priya Sharma / sharam fuzzy query; active in Offer |
| `aarav-patel` | Aarav Patel | Screening | active | Sun 20 Sep 2026, 14:00 IST | Applied → Screening | Match 1 for stuck in Screening > 7 days (active 10 days in Screening) |
| `kavya-reddy` | Kavya Reddy | Screening | active | Fri 18 Sep 2026, 14:00 IST | Applied → Screening | Match 2 for stuck in Screening > 7 days (active 12 days in Screening) |
| `rohan-mehta` | Rohan Mehta | Screening | active | Wed 16 Sep 2026, 14:00 IST | Applied → Screening | Match 3 for stuck in Screening > 7 days (active 14 days in Screening) |
| `ananya-deshmukh` | Ananya Deshmukh | Screening | active | Sun 27 Sep 2026, 14:00 IST | Applied → Screening | Decoy 1 for stuck > 7 days (active in Screening for 3 days) |
| `vikram-joshi` | Vikram Joshi | Screening | active | Sat 26 Sep 2026, 14:00 IST | Applied → Screening | Decoy 2 for stuck > 7 days (active in Screening for 4 days) |
| `siddharth-rao` | Siddharth Rao | Screening | rejected | Wed 30 Sep 2026, 12:00 IST | Applied → Screening | Decoy 3 for stuck > 7 days (spent 12 days in Screening, but rejected at Screening); match for rejected at Screening |
| `aditi-nair` | Aditi Nair | Screening | active | Wed 23 Sep 2026, 14:00 IST | Applied → Screening | Boundary test: active in Screening exactly 7x24h (168h) at NOW_A. Excluded by `gt 7`, included by `gte 7` |
| `arjun-chatterjee` | Arjun Chatterjee | Offer | active | Wed 30 Sep 2026, 01:36 IST | Applied → Screening → Interview → Offer | Match 2 for moved to Interview since Monday; currently active at Offer; drives INCLUDE_PENDING hint |
| `divya-singh` | Divya Singh | Interview | rejected | Wed 30 Sep 2026, 04:42 IST | Applied → Screening → Interview | Match 3 for moved to Interview since Monday; rejected at Interview; match 1 for rejected at Interview |
| `kabir-bhatia` | Kabir Bhatia | Interview | active | Fri 25 Sep 2026, 14:00 IST | Applied → Screening → Interview | Decoy 1 for moved to Interview since Monday (moved 5 days ago); active in Interview; candidate with no email |
| `neha-gupta` | Neha Gupta | Offer | active | Sun 27 Sep 2026, 06:00 IST | Applied → Screening → Interview → Offer | Decoy 2 for moved to Interview since Monday (moved 6 days ago); active at Offer |
| `dhruv-kapoor` | Dhruv Kapoor | Offer | rejected | Mon 28 Sep 2026, 22:00 IST | Applied → Screening → Interview → Offer | Match 1 for reached Offer but didn't get hired (reached Offer, rejected at Offer) |
| `tanya-saxena` | Tanya Saxena | Offer | rejected | Mon 28 Sep 2026, 12:00 IST | Applied → Screening → Interview → Offer | Match 2 for reached Offer but didn't get hired (reached Offer, rejected at Offer) |
| `ishaan-malhotra` | Ishaan Malhotra | Offer | rejected | Mon 28 Sep 2026, 02:00 IST | Applied → Screening → Interview → Offer | Match 3 for reached Offer but didn't get hired (reached Offer, rejected at Offer) |
| `varun-verma` | Varun Verma | Hired | hired | Tue 22 Sep 2026, 06:00 IST | Applied → Screening → Interview → Offer → Hired | Hired candidate 1; decoy for reached offer but didn't get hired |
| `meera-iyer` | Meera Iyer | Hired | hired | Sun 20 Sep 2026, 04:00 IST | Applied → Screening → Interview → Offer → Hired | Hired candidate 2; decoy for reached offer but didn't get hired |
| `sanjay-kulkarni` | Sanjay Kulkarni | Interview | rejected | Tue 29 Sep 2026, 08:00 IST | Applied → Screening → Interview | Match 2 for rejected at Interview |
| `tarun-banerjee` | Tarun Banerjee | Applied | rejected | Sat 26 Sep 2026, 10:00 IST | Applied | Match for rejected at Applied |
| `yash-chawla` | Yash Chawla | Interview | active | Sun 27 Sep 2026, 20:00 IST | Applied → Screening → Interview | Short stay in Interview <= 3 days (entered Interview 66h ago); match for `lte 3 days` query |
| `pooja-mishra` | Pooja Mishra | Interview | active | Sun 27 Sep 2026, 02:00 IST | Applied → Screening → Interview | Candidate with NOTE events; active in Interview |
| `rahul-dasgupta` | Rahul Dasgupta | Screening | active | Sat 26 Sep 2026, 20:00 IST | Applied → Screening | Candidate with NOTE event; active in Screening; candidate without email |
| `zoya-sengupta` | Zoya Sengupta | Applied | active | Tue 29 Sep 2026, 14:00 IST | Applied | Active in Applied for 24 hours; baseline active candidate |

## §2 Golden Queries at NOW_A (Asia/Kolkata)

Reference time `NOW_A`: `2026-09-30T14:00:00+05:30` (`2026-09-30T08:30:00Z`).

### 1. `Find Priya Sharma` (brief-1)
- **Expected AST:**
  ```json
  {"clauses": [], "name_terms": ["priya", "sharma"], "source": "rules"}
  ```
- **Ordered Results:**
  1. `priya-sharma` | Score: `1.0` | Reasons: `["Name: \"priya\" = Priya", "Name: \"sharma\" = Sharma"]`
  2. `priyanka-sharma` | Score: `0.99` | Reasons: `["Name: \"priya\" → Priyanka (prefix)", "Name: \"sharma\" = Sharma"]`
  3. `riya-sharman` | Score: `0.91` | Reasons: `["Name ≈ \"priya\" → Riya (1 edit)", "Name: \"sharma\" → Sharman (prefix)"]`
- **Decoys Excluded:**
  - `pria-verma`: score 0.429 (< 0.75 threshold).
  - All other candidates: name score < 0.75.
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 2. `sharam` (brief-2)
- **Expected AST:**
  ```json
  {"clauses": [], "name_terms": ["sharam"], "source": "rules"}
  ```
- **Ordered Results:**
  1. `priya-sharma` | Score: `0.9` | Reasons: `['Name ≈ "sharam" → Sharma (1 edit)']`
  2. `priyanka-sharma` | Score: `0.9` | Reasons: `['Name ≈ "sharam" → Sharma (1 edit)']`
  3. `riya-sharman` | Score: `0.874` | Reasons: `['Name ≈ "sharam" → Sharman (2 edits)']`
- **Decoys Excluded:**
  - `pria-verma`: no token matching "sharam" within budget.
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 3. `Who's in Interview right now?` (brief-3)
- **Expected AST:**
  ```json
  {"clauses": [{"kind": "current_stage", "stages": ["Interview"]}], "name_terms": [], "source": "rules"}
  ```
- **Ordered Results:**
  1. `priya-sharma` | Score: `1.0` | Reasons: `["In Interview stage"]`
  2. `yash-chawla` | Score: `0.75` | Reasons: `["In Interview stage"]`
  3. `pooja-mishra` | Score: `0.5` | Reasons: `["In Interview stage"]`
  4. `kabir-bhatia` | Score: `0.25` | Reasons: `["In Interview stage"]`
- **Decoys Excluded:**
  - `divya-singh`, `sanjay-kulkarni`: status is `rejected` (rejected at Interview).
  - `arjun-chatterjee`, `neha-gupta`, `riya-sharman`: current stage is `Offer`.
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 4. `Stuck in Screening for more than a week` (brief-4)
- **Expected AST:**
  ```json
  {"clauses": [{"kind": "time_in_stage", "stage": "Screening", "op": "gt", "days": 7.0}], "name_terms": [], "source": "rules"}
  ```
- **Ordered Results:**
  1. `rohan-mehta` | Score: `1.0` | Reasons: `["In Screening for 14 days (>7 days target)"]`
  2. `kavya-reddy` | Score: `0.67` | Reasons: `["In Screening for 12 days (>7 days target)"]`
  3. `aarav-patel` | Score: `0.33` | Reasons: `["In Screening for 10 days (>7 days target)"]`
- **Decoys Excluded:**
  - `aditi-nair`: in Screening for exactly 7.0 days (168h). `gt 7.0` requires > 7.0 days strictly.
  - `ananya-deshmukh` (3 days), `vikram-joshi` (4 days): <= 7 days.
  - `siddharth-rao`: spent 12 days in Screening, but status is `rejected` (stuck applies to active only).
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 5. `Who moved to Interview since Monday?` (brief-5)
- **Expected AST:**
  ```json
  {"clauses": [{"kind": "moved_to", "target": "Interview", "since": "2026-09-27T18:30:00Z", "until": null}], "name_terms": [], "source": "rules"}
  ```
- **Ordered Results:**
  1. `priya-sharma` | Score: `1.0` | Reasons: `["Moved to Interview on Tue 29 Sep 2026, 00:48 IST"]`
  2. `divya-singh` | Score: `0.67` | Reasons: `["Moved to Interview on Mon 28 Sep 2026, 18:36 IST"]`
  3. `arjun-chatterjee` | Score: `0.33` | Reasons: `["Moved to Interview on Mon 28 Sep 2026, 12:24 IST"]`
- **Decoys Excluded:**
  - `kabir-bhatia` (moved Fri 25 Sep), `neha-gupta` (moved Sat 26 Sep), `yash-chawla` (moved Sun 27 Sep): moved before Monday 00:00 IST.
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 6. `Who reached the Offer stage but didn't get hired?` (brief-6)
- **Expected AST:**
  ```json
  {"clauses": [{"kind": "reached", "stage": "Offer", "negate": false}, {"kind": "status", "status": "rejected", "negate": false}], "name_terms": [], "source": "rules"}
  ```
- **Ordered Results:**
  1. `dhruv-kapoor` | Score: `1.0` | Reasons: `["Reached Offer · Rejected on Mon 28 Sep 2026, 22:00 IST", "Status: rejected"]`
  2. `tanya-saxena` | Score: `0.67` | Reasons: `["Reached Offer · Rejected on Mon 28 Sep 2026, 12:00 IST", "Status: rejected"]`
  3. `ishaan-malhotra` | Score: `0.33` | Reasons: `["Reached Offer · Rejected on Mon 28 Sep 2026, 02:00 IST", "Status: rejected"]`
- **Decoys Excluded:**
  - `varun-verma`, `meera-iyer`: status is `hired` (not rejected).
  - `arjun-chatterjee`, `neha-gupta`, `riya-sharman`: status is `active` (pending at Offer).
- **Hints / Warnings:** `hints: ["INCLUDE_PENDING"]`

### 7. `priya moved to interview since monday` (combo-1)
- **Expected AST:**
  ```json
  {"clauses": [{"kind": "moved_to", "target": "Interview", "since": "2026-09-27T18:30:00Z", "until": null}], "name_terms": ["priya"], "source": "rules"}
  ```
- **Ordered Results:**
  1. `priya-sharma` | Score: `1.0` | Reasons: `["Name: \"priya\" = Priya", "Moved to Interview on Tue 29 Sep 2026, 00:48 IST"]`
- **Decoys Excluded:**
  - `divya-singh`, `arjun-chatterjee`: moved since Monday, but name does not match "priya".
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 8. `stuck in screening over a week except rejected` (combo-2)
- **Expected AST:**
  ```json
  {"clauses": [{"kind": "time_in_stage", "stage": "Screening", "op": "gt", "days": 7.0}, {"kind": "status", "status": "rejected", "negate": true}], "name_terms": [], "source": "rules"}
  ```
- **Ordered Results:**
  1. `rohan-mehta` | Score: `1.0` | Reasons: `["In Screening for 14 days (>7 days target)", "Status: Not rejected"]`
  2. `kavya-reddy` | Score: `0.67` | Reasons: `["In Screening for 12 days (>7 days target)", "Status: Not rejected"]`
  3. `aarav-patel` | Score: `0.33` | Reasons: `["In Screening for 10 days (>7 days target)", "Status: Not rejected"]`
- **Decoys Excluded:**
  - `siddharth-rao`: rejected at Screening (status = rejected).
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 9. `priya in interview` (combo-3)
- **Expected AST:**
  ```json
  {"clauses": [{"kind": "current_stage", "stages": ["Interview"]}], "name_terms": ["priya"], "source": "rules"}
  ```
- **Ordered Results:**
  1. `priya-sharma` | Score: `1.0` | Reasons: `["Name: \"priya\" = Priya", "In Interview stage"]`
- **Decoys Excluded:**
  - `pria-verma`: in Applied stage.
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 10. `in screening for more than 5 days and added this week` (combo-4, EMPTY_RESULT example)
- **Expected AST:**
  ```json
  {"clauses": [{"kind": "time_in_stage", "stage": "Screening", "op": "gt", "days": 5.0}, {"kind": "added", "since": "2026-09-27T18:30:00Z", "until": null}], "name_terms": [], "source": "rules"}
  ```
- **Ordered Results:** `[]` (EMPTY_RESULT)
- **Decoys / Counterfactual Analysis:**
  - Clause 1 (`in screening > 5d`) matches 4 candidates: `rohan-mehta`, `kavya-reddy`, `aarav-patel`, `aditi-nair`.
  - Clause 2 (`added this week`) matches 2 candidates: `pria-verma`, `zoya-sengupta`.
  - Intersection is `[]`.
  - Dropping Clause 2 (`added this week`) leaves 4 matches.
- **Hints / Warnings:** `hints: [{"code": "EMPTY_RESULT", "message": "No one matches all 2 conditions. Without 'added this week' there would be 4.", "hint": null}]`

### 11. `rejected at interview` (rejected-at-1)
- **Expected AST:**
  ```json
  {"clauses": [{"kind": "status", "status": "rejected", "negate": false, "at_stage": "Interview"}], "name_terms": [], "source": "rules"}
  ```
- **Ordered Results:**
  1. `divya-singh` | Score: `1.0` | Reasons: `["Rejected at Interview stage on Wed 30 Sep 2026, 04:42 IST"]`
  2. `sanjay-kulkarni` | Score: `0.5` | Reasons: `["Rejected at Interview stage on Tue 29 Sep 2026, 08:00 IST"]`
- **Decoys Excluded:**
  - `siddharth-rao`: rejected at Screening.
  - `tarun-banerjee`: rejected at Applied.
  - `dhruv-kapoor`, `tanya-saxena`, `ishaan-malhotra`: rejected at Offer.
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 12. `stuck in screening for at least a week` (gte-1)
- **Expected AST:**
  ```json
  {"clauses": [{"kind": "time_in_stage", "stage": "Screening", "op": "gte", "days": 7.0}], "name_terms": [], "source": "rules"}
  ```
- **Ordered Results:**
  1. `rohan-mehta` | Score: `1.0` | Reasons: `["In Screening for 14 days (≥7 days target)"]`
  2. `kavya-reddy` | Score: `0.75` | Reasons: `["In Screening for 12 days (≥7 days target)"]`
  3. `aarav-patel` | Score: `0.5` | Reasons: `["In Screening for 10 days (≥7 days target)"]`
  4. `aditi-nair` | Score: `0.25` | Reasons: `["In Screening for 7 days (≥7 days target)"]`

- **Boundary Difference:** Includes `aditi-nair` (exactly 7.0 days in Screening at NOW_A), who was excluded by `gt 7`.
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 13. `priya` (priya-1)
- **Expected AST:**
  ```json
  {"clauses": [], "name_terms": ["priya"], "source": "rules"}
  ```
- **Ordered Results:**
  1. `priya-sharma` | Score: `1.0` | Reasons: `["Name: \"priya\" = Priya"]`
  2. `priyanka-sharma` | Score: `0.95` | Reasons: `["Name: \"priya\" → Priyanka (prefix)"]`
  3. `pria-verma` | Score: `0.888` | Reasons: `["Name ≈ \"priya\" → Pria (1 edit)"]`
  4. `riya-sharman` | Score: `0.87` | Reasons: `["Name ≈ \"priya\" → Riya (1 edit)"]`
- **Decoys Excluded:**
  - Candidates without name tokens matching "priya" within budget.
- **Hints / Warnings:** `errors: []`, `warnings: []`, `hints: []`

### 14. Invalid Queries

1. **`in onboarding`** (inv-1)
   - **AST:** `null`
   - **Errors:** `[{"code": "UNKNOWN_STAGE", "message": "\"onboarding\" isn't a stage. Stages are Applied, Screening, Interview, Offer, Hired.", "hint": null}]`
2. **`stuck in hired`** (inv-2)
   - **AST:** `null`
   - **Errors:** `[{"code": "FINAL_STAGE_STUCK", "message": "Hired is a final outcome — candidates can't be stuck there.", "hint": null}]`
3. **`moved to applied since monday`** (inv-3)
   - **AST:** `null`
   - **Errors:** `[{"code": "START_STAGE_MOVE", "message": "Everyone starts in Applied. Did you mean 'added since Monday'?", "hint": null}]`
4. **`in interview and in offer`** (inv-4)
   - **AST:** `null`
   - **Errors:** `[{"code": "CONTRADICTION", "message": "Cannot be in Interview and in Offer simultaneously.", "hint": null}]`

---

## §3 Monday-is-Today Check (NOW_B)

Reference time **`NOW_B`**: `2026-09-28T09:00:00+05:30` (Monday 09:00 IST).
Query: `"Who moved to Interview since Monday?"`

- **AST Resolution:** `since = 2026-09-27T18:30:00Z` (Monday-is-today rule resolves "since Monday" to 00:00 IST of today, 28 Sep 2026).
- **Matched Candidate Keys at NOW_B:**
  1. `priya-sharma`
  2. `divya-singh`
  3. `arjun-chatterjee`
- **Result Comparison:** Identical candidate set and ordering as evaluated under `NOW_A`.

---

## §4 How This Was Computed

Computed mechanically via the throwaway oracle script `private/oracle.py`:
```powershell
uv run --no-project --with rapidfuzz --with tzdata python private/oracle.py
```

### Raw Oracle Output

```text
[PASS] Chronology verified across NOW_A, NOW_B, MONDAY_0005.
[PASS] Lexicon collision check passed (no name token within 1 edit of lexicon words).

--- FUZZY SCORES WITHIN ±0.05 OF 0.75 THRESHOLD (0.70 TO 0.80) & PRIA VERMA SCAN ---

Query: 'Find Priya Sharma' (terms: ['priya', 'sharma'])
  - pria-verma ('Pria Verma') score for 'Find Priya Sharma': 0.4767
  - Candidates in [0.70, 0.80]: (None)

Query: 'sharam' (terms: ['sharam'])
  - pria-verma ('Pria Verma') score for 'sharam': 0.0000
  - Candidates in [0.70, 0.80]: (None)

Query: 'priya moved to interview since monday' (terms: ['priya'])
  - pria-verma ('Pria Verma') score for 'priya moved to interview since monday': 0.9833
  - Candidates in [0.70, 0.80]: (None)

Query: 'priya in interview' (terms: ['priya'])
  - pria-verma ('Pria Verma') score for 'priya in interview': 0.9833
  - Candidates in [0.70, 0.80]: (None)
[PASS] Written 54 lines to tests/evals/queries.jsonl
[PASS] Diff of ids and categories between queries.jsonl and SEARCH_SPEC §13: 0 mismatches.
JSONL category counts: {'brief': 6, 'paraphrase': 8, 'combo': 9, 'typo': 4, 'invalid': 13, 'edge': 6, 'power': 2, 'llm': 2, 'injection': 4}

=======================================================
GOLDEN QUERIES EVALUATION AT NOW_A
=======================================================

QUERY [brief-1]: 'Find Priya Sharma'
Matched Keys (3): ['priya-sharma', 'priyanka-sharma', 'riya-sharman']
  - priya-sharma (Priya Sharma) | Score: 1.0 | Reasons: ['Name: "priya" = Priya', 'Name: "sharma" = Sharma']
  - priyanka-sharma (Priyanka Sharma) | Score: 0.99 | Reasons: ['Name: "priya" → Priyanka (prefix)', 'Name: "sharma" = Sharma']
  - riya-sharman (Riya Sharman) | Score: 0.96 | Reasons: ['Name ≈ "priya" → Riya (1 edit)', 'Name: "sharma" → Sharman (prefix)']

QUERY [brief-2]: 'sharam'
Matched Keys (3): ['priya-sharma', 'priyanka-sharma', 'riya-sharman']
  - priya-sharma (Priya Sharma) | Score: 1.0 | Reasons: ['Name ≈ "sharam" → Sharma (1 edit)']
  - priyanka-sharma (Priyanka Sharma) | Score: 1.0 | Reasons: ['Name ≈ "sharam" → Sharma (1 edit)']
  - riya-sharman (Riya Sharman) | Score: 0.97 | Reasons: ['Name ≈ "sharam" → Sharman (2 edits)']

QUERY [brief-3]: 'Who's in Interview right now?'
Matched Keys (4): ['priya-sharma', 'yash-chawla', 'pooja-mishra', 'kabir-bhatia']
  - priya-sharma (Priya Sharma) | Score: 1.0 | Reasons: ['In Interview stage']
  - yash-chawla (Yash Chawla) | Score: 0.75 | Reasons: ['In Interview stage']
  - pooja-mishra (Pooja Mishra) | Score: 0.5 | Reasons: ['In Interview stage']
  - kabir-bhatia (Kabir Bhatia) | Score: 0.25 | Reasons: ['In Interview stage']

QUERY [brief-4]: 'Stuck in Screening for more than a week'
Matched Keys (3): ['rohan-mehta', 'kavya-reddy', 'aarav-patel']
  - rohan-mehta (Rohan Mehta) | Score: 1.0 | Reasons: ['In Screening for 14 days (>7 days target)']
  - kavya-reddy (Kavya Reddy) | Score: 0.67 | Reasons: ['In Screening for 12 days (>7 days target)']
  - aarav-patel (Aarav Patel) | Score: 0.33 | Reasons: ['In Screening for 10 days (>7 days target)']

QUERY [brief-5]: 'Who moved to Interview since Monday?'
Matched Keys (3): ['priya-sharma', 'divya-singh', 'arjun-chatterjee']
  - priya-sharma (Priya Sharma) | Score: 1.0 | Reasons: ['Moved to Interview on Tue 29 Sep 2026, 00:48 IST']
  - divya-singh (Divya Singh) | Score: 0.67 | Reasons: ['Moved to Interview on Mon 28 Sep 2026, 18:36 IST']
  - arjun-chatterjee (Arjun Chatterjee) | Score: 0.33 | Reasons: ['Moved to Interview on Mon 28 Sep 2026, 12:24 IST']

QUERY [brief-6]: 'Who reached the Offer stage but didn't get hired?'
Matched Keys (3): ['dhruv-kapoor', 'tanya-saxena', 'ishaan-malhotra']
  - dhruv-kapoor (Dhruv Kapoor) | Score: 1.0 | Reasons: ['Reached Offer · Rejected on Mon 28 Sep 2026, 22:00 IST', 'Status: rejected']
  - tanya-saxena (Tanya Saxena) | Score: 0.67 | Reasons: ['Reached Offer · Rejected on Mon 28 Sep 2026, 12:00 IST', 'Status: rejected']
  - ishaan-malhotra (Ishaan Malhotra) | Score: 0.33 | Reasons: ['Reached Offer · Rejected on Mon 28 Sep 2026, 02:00 IST', 'Status: rejected']

QUERY [combo-1]: 'priya moved to interview since monday'
Matched Keys (1): ['priya-sharma']
  - priya-sharma (Priya Sharma) | Score: 1.0 | Reasons: ['Name: "priya" = Priya', 'Moved to Interview on Tue 29 Sep 2026, 00:48 IST']

QUERY [combo-2]: 'stuck in screening over a week except rejected'
Matched Keys (3): ['rohan-mehta', 'kavya-reddy', 'aarav-patel']
  - rohan-mehta (Rohan Mehta) | Score: 1.0 | Reasons: ['In Screening for 14 days (>7 days target)', 'Status: Not rejected']
  - kavya-reddy (Kavya Reddy) | Score: 0.67 | Reasons: ['In Screening for 12 days (>7 days target)', 'Status: Not rejected']
  - aarav-patel (Aarav Patel) | Score: 0.33 | Reasons: ['In Screening for 10 days (>7 days target)', 'Status: Not rejected']

QUERY [combo-3]: 'priya in interview'
Matched Keys (1): ['priya-sharma']
  - priya-sharma (Priya Sharma) | Score: 1.0 | Reasons: ['Name: "priya" = Priya', 'In Interview stage']

QUERY [combo-4]: 'in screening for more than 5 days and added this week'
Matched Keys (0): []

QUERY [rejected-at-1]: 'rejected at interview'
Matched Keys (2): ['divya-singh', 'sanjay-kulkarni']
  - divya-singh (Divya Singh) | Score: 1.0 | Reasons: ['Rejected at Interview stage on Wed 30 Sep 2026, 04:42 IST']
  - sanjay-kulkarni (Sanjay Kulkarni) | Score: 0.5 | Reasons: ['Rejected at Interview stage on Tue 29 Sep 2026, 08:00 IST']

QUERY [gte-1]: 'stuck in screening for at least a week'
Matched Keys (4): ['rohan-mehta', 'kavya-reddy', 'aarav-patel', 'aditi-nair']
  - rohan-mehta (Rohan Mehta) | Score: 1.0 | Reasons: ['In Screening for 14 days (≥7 days target)']
  - kavya-reddy (Kavya Reddy) | Score: 0.75 | Reasons: ['In Screening for 12 days (≥7 days target)']
  - aarav-patel (Aarav Patel) | Score: 0.5 | Reasons: ['In Screening for 10 days (≥7 days target)']
  - aditi-nair (Aditi Nair) | Score: 0.25 | Reasons: ['In Screening for 7 days (≥7 days target)']

--- MONDAY-IS-TODAY CHECK AT NOW_B FOR BRIEF-5 ---
Matched Keys at NOW_B (3): ['priya-sharma', 'divya-singh', 'arjun-chatterjee']
[PASS] Results at NOW_B match results at NOW_A for 'moved to interview since monday'.

--- PROOF: SCORE NORMALIZATION FOR 'everyone except rejected' (edge-4) ---
Result count n = 19
Scores list: [1.0, 0.95, 0.89, 0.84, 0.79, 0.74, 0.68, 0.63, 0.58, 0.53, 0.47, 0.42, 0.37, 0.32, 0.26, 0.21, 0.16, 0.11, 0.05]
Min score = 0.05, Max score = 1.0
[PASS] Scores for non-name query are strictly within (0, 1].
```

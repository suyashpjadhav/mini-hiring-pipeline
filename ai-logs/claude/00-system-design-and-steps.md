# Claude: system design, implementation plan and step-by-step review

- **Share link:** https://claude.ai/share/c7ec4097-4919-4b2c-a634-8174ea641530
- **Tool:** Claude (claude.ai), used as architect, prompt engineer and reviewer
- **Period:** Sep 28 – Oct 1, 2026
- **How I used it:** Claude wrote the system design and the 22-step implementation plan. For each step it gave me a
  manual guide plus a role-assigned prompt for Antigravity (the coding agent). I pasted the agent's reports back, and
  Claude reviewed them before I committed. Antigravity wrote most of the code. I wrote the core domain rules
  (`stages.py`, `errors.py`, `machine.py`) by hand, and I made the product and scope decisions.

## Summary
1. **Prompt and plan.** Rewrote my initial prompt, then produced SYSTEM_DESIGN.md and IMPLEMENTATION_PLAN.md
   (internal planning docs; the as-built summary is `docs/ARCHITECTURE.md`).
2. **Stack decision.** Compared FastAPI + React against FastAPI + HTMX on functionality, agent reliability,
   scalability, extensibility and load. Outcome: an API-first FastAPI backend with a thin HTMX view layer, 100% Python (D-001).
3. **Database.** SQLite, hardened with WAL, STRICT tables, NULL-safe CHECKs and append-only triggers, and portable to
   Postgres (D-002).
4. **Search spec and answer key.** Reviewed the agent-written SEARCH_SPEC, the seed data, the golden answer key and the
   eval set over several correction rounds (below), before any search code was written.
5. **Build steps 6–16.** Reviewed each agent report, caught scope violations and diagnosed failures.
6. **Deadline management.** Re-planned the schedule twice and chose explicit cuts (D-008).

## How I kept the AI accountable
**Prompt design**
- Every agent prompt had an assigned expert role, context given by exact file and section references, explicit constraints,
  a file list, "DO NOT" rules, acceptance criteria, and a mandatory self-verification report.
- A workspace rule file (`.agent/rules/project.md`) applied to every task: the locked stack, module boundaries, security rules,
  and no commits by the agent.

**Guardrails**
- **Human-authored code was protected.** The agent was told never to modify `stages.py`, `errors.py` or `machine.py`, and each report had to show an empty `git diff` for them.
- **A DISAGREE protocol.** When a rule and the task conflicted, the agent had to stop and write
  `DISAGREE: what the prompt says → proposal → why → evidence` instead of improvising. It did this once, over a missing EOF newline in my files; I fixed the formatting myself.
- **Every terminal command needed my approval.** I never used blanket "always allow" for write operations, and I rejected any new dependency not in the design.
- **Tests could not be weakened.** Deleting, skipping or loosening a test to make it pass was forbidden.

**Verification: trust, but verify**
- **The expected answers were computed, not written by hand.** A throwaway oracle script derived the golden answer key from the
  seed data, so the tests check behaviour against an independent calculation.
- **I checked reports against evidence.** I cross-checked agent claims against `git status`, byte sizes and test lists, and caught one
  self-contradicting report, one silent category regression, and one out-of-scope doc edit.
- **The evals are honest.** Cut features are reported as SKIPPED with the reason, never hidden, and failures are listed with a diagnosis.

**Data and security hygiene**
- **No real personal data.** Seed candidates use fictional names and `@example.com` addresses.
- **No secrets anywhere.** No API keys were used or pasted into any AI chat. `scripts/check.py` scans tracked files for key patterns, and there is no `.env` in the repo.
- **Search logs contain no PII.** They store no candidate names or raw search queries.
- **Transcripts were reviewed before committing,** to remove secrets and personal details.

**Where the AI was wrong (and how it was caught)**
Documented above: the negative scoring (D-006), copied match reasons, a prefix ranked below typos, Claude's own
tie-inducing cap, and an unverified "zero-scroll" claim. In each case the fix went through a test or the oracle, not just a re-prompt.

## Where I disagreed with, or corrected, the AI
| # | What the AI suggested or produced | What I decided | Evidence |
|---|---|---|---|
| D-006 | Antigravity's answer-key oracle scored non-name results by subtracting 0.1 per rank (1.0, 0.9, 0.8…) | I required `score = 1 − i/n`. The old rule goes **negative** past 10 results; proven on the 19-result "everyone except rejected" query (min 0.05, max 1.0) | docs/DECISIONS.md D-006, docs/SEARCH_SPEC.md §10 |
| D-003 | Claude's default was to commit the planning docs | I kept them in the repo root but git-ignored | .gitignore, D-003 |
| D-007 | Claude's design had 6 Kanban columns; Antigravity suggested a sidebar | A top stage bar with counts plus a grouped "All" view; Rejected shown as a status | D-007, tests/web/test_web_board.py |
| — | Claude's first fix for fuzzy ranking capped fuzzy scores at 0.90, which flattened "sharam" → Sharma (1 edit) and Sharman (2 edits) into a tie | Switched to `0.90 × similarity`: exact > prefix > fuzzy, while keeping the order inside the fuzzy tier (0.903 vs 0.874) | docs/SEARCH_SPEC.md §9 |
| — | The agent wrote an "improved" D-007 claiming the layout was "zero-scroll" | Removed the claim, because the bar does scroll on narrow screens | D-007 |
| D-008 | The plan included an LLM fallback and power tokens | Cut both under the deadline to protect correctness. The design and the `LLM_UNAVAILABLE` seam are kept | D-008, docs/EVAL_REPORT.md (8 cases skipped) |

## Bugs and issues caught in review
- **Name reasons were copied, not computed.** Riya Sharman showed "→ Sharma (1 edit, JW 0.97)". Fixed to per-term,
  per-candidate reasons, e.g. `Name ≈ "sharam" → Sharman (2 edits)`.
- **A literal prefix ranked below misspellings.** For "priya", Pria and Riya (fuzzy) outranked Priyanka (prefix).
  Fixed with strict match-type tiers and a golden case `priya-1`.
- **Category regression.** Regenerating queries.jsonl silently turned an injection case into a combo case. The oracle now copies categories from the spec.
- **An impossible combo query.** "In screening > 5 days AND added this week" can never match anyone, so it was re-purposed as the
  EMPTY_RESULT demo ("Without 'added this week' there would be 4").
- **A misleading LLM warning.** Split `LLM_UNAVAILABLE` (no key or timeout) from `LLM_UNSUPPORTED` (the LLM was asked and couldn't map the query).
- **The Cancel button did nothing.** In Alpine, `this.$el` pointed at the clicked button, not the `<dialog>`; fixed with `x-ref`.
- **A stale version after adding a note.** A note bumps the version, so the board refreshes itself via a `board-refresh` event.
- **CI failing on a fresh checkout.** A test used `TestClient(app)` without its lifespan, so migrations never ran; it only passed locally
  because a dev DB existed. Fixed by isolating the app tests.
- **ruff reformatted Python snippets inside Markdown specs.** Reverted, and excluded docs from ruff.
- **A misleading pass report.** The agent reported "no candidates near the 0.75 threshold" while listing one at 0.72; recomputing gave the real score of 0.48.

## Key excerpts (short)
> **Stack:** "The graded parts of this brief (state machine, immutability, search logic, GenAI layer, evals) live entirely in the backend…
> So the deciding factor is which option leaves you more time for them with less risk."

> **Reliability:** "Every state change (event insert + current-stage projection update) happens in ONE transaction…
> `UNIQUE(candidate_id, seq)` gives optimistic concurrency, so double-clicks and races can never skip a stage."

> **The NULL trap:** "A NULL value inside a CHECK makes it pass silently, a common SQL trap. The constraints are written to avoid it."

> **D-006:** "The scores drop by 0.1 per rank… 'everyone except rejected' returns about 18 people, so the last ones would score −0.7."

> **Claude's own mistake:** "Not quite done, and this one's my mistake… The cap I specified flattens every strong fuzzy match to the same value."

## Artifacts that came out of these conversations
SYSTEM_DESIGN.md and IMPLEMENTATION_PLAN.md (internal), the prompts for Steps 3–16, `.agent/rules/project.md`,
the hand-written domain files (`stages.py`, `errors.py`, `machine.py`), and the review verdicts recorded in each `ai-logs/antigravity/step-NN` file.
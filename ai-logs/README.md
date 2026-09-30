# AI chat logs

All AI assistance used to build this project, kept as raw as possible.

## Layout
- `claude/`: design and planning conversations with Claude (share link, summary and key excerpts).
- `antigravity/`: one file per Antigravity conversation, which is one per implementation step (`step-NN-<slug>.md`).

## Per-file template
```
# Step NN — <title>
- Date:
- Tool / model / mode: Antigravity · <model> · <Planning|Fast>
- Prompt: <pasted or summarised>

## Summary
## Files changed
## Decisions and disagreements
## Issues hit and fixes
## Verification evidence
## Raw transcript
<!-- pasted by the human, unedited apart from removed secrets or personal data -->
```

## Index
| File | Step | What was decided or built |
|---|---|---|
| claude/00-system-design-and-steps.md | 0 | System design, implementation plan, stack decisions |
| antigravity/step-03-agent-rules.md | 3 | Agent rules, /check workflow, decisions log |
| antigravity/step-04-search-spec.md | 4 | Search spec, AST reference, validator catalog, fuzzy math, 46-case example catalogue |
| antigravity/step-05-seed-and-answer-key.md | 5 | Seed dataset (26 candidates), golden answer key at NOW_A/NOW_B, eval dataset (54 queries), test plan |
| antigravity/step-06-scaffold.md | 6 | Scaffold app, core infra, quality gates, CI |
| antigravity/step-07-domain.md | 7 | Pure domain models (events, projection, hash chain) and unit/property tests |
| antigravity/step-08-persistence.md | 8 | Event store, db-enforced immutability, Alembic migration, PipelineService |
| antigravity/step-10-theme-security.md | 10 | Design tokens, base layout shell, double-submit CSRF, strict CSP and security headers middleware |
| antigravity/step-11-board.md | 11 | Kanban board grouped by stage, add candidate modal, advance and reject HTMX routes |
| antigravity/step-12-drawer.md | 12 | Candidate detail drawer, live stage timer, audit timeline, history verified badge, and add note route |
| antigravity/step-13-search-engine.md | 13 | Search engine: deterministic rule parser, validator, SQLAlchemy Core repo, ranker, explanations, and golden test suite |


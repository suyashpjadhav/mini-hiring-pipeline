---
description: Run all quality gates and report pass/fail with first errors
---

1. Run `git status` and list any uncommitted files.
2. If `scripts/check.py` exists, run `uv run python -m scripts.check`. Otherwise report: "Quality gate not scaffolded yet (arrives in Step 6)."
3. Report each gate as PASS/FAIL. For each failure, show the first error and propose a fix. Do not apply fixes without approval.

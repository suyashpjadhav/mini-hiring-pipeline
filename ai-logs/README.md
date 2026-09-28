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

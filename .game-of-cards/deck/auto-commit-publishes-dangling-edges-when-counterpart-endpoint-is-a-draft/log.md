## 2026-11-09T01:55:44Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/engine.py:5710`
(`print(f"ERROR: adding {advancer} → {title} would create a cycle in the`), moved by `371e1806`;
`engine.py:5426` (`print(f"Next: edit {rel}/README.md to fill the body and DoD; then ask`), moved by `ad7e895b`.
Reproducer: `reproduce.py` → exit 1, AssertionError in its own setup: `goc publish parent-card` now refuses a card with no `summary:`, so the `goc advance` step under test never runs — the harness broke, not the defect. A scratch copy that only adds a `summary:` line before publishing prints "DEFECT: committed tree has parent-card.advanced_by -> 'draft-epic' but no such card dir in HEAD" (exit 1).
Verdict: not verified (reproducer crashed: setup assertion, publish requires `summary:`) — needs a human re-read.
As filed, these cites sat 6 lines above the code their prose names; re-anchored to that code: `goc/engine.py:6577` and Option A's `:5710` → `:7429` (`_cmd_advance`'s pair `_git_auto_commit`), `engine.py:6293-6298` → `:7099-7104` (`goc new --commit`, `exclude_draft=False`).
Gate unchanged.

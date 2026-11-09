## 2026-11-09T01:55:44Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/engine.py:5710`
(`print(f"ERROR: adding {advancer} → {title} would create a cycle in the`), moved by `371e1806`;
`engine.py:5426` (`print(f"Next: edit {rel}/README.md to fill the body and DoD; then ask`), moved by `ad7e895b`.
Reproducer: `reproduce.py` → exit 1, AssertionError in its own setup: `goc publish parent-card` now refuses a card with no `summary:`, so the `goc advance` step under test never runs — the harness broke, not the defect. A scratch copy that only adds a `summary:` line before publishing prints "DEFECT: committed tree has parent-card.advanced_by -> 'draft-epic' but no such card dir in HEAD" (exit 1).
Verdict: not verified (reproducer crashed: setup assertion, publish requires `summary:`) — needs a human re-read.
As filed, these cites sat 6 lines above the code their prose names; re-anchored to that code: `goc/engine.py:6577` and Option A's `:5710` → `:7429` (`_cmd_advance`'s pair `_git_auto_commit`), `engine.py:6293-6298` → `:7099-7104` (`goc new --commit`, `exclude_draft=False`).
Gate unchanged.

## 2026-11-09T02:15:36Z — Cites were written against the tree before 6d36c3dc

Why this card's `engine.py` numbers sat six lines above the code its prose
names: they were computed against the tree before `6d36c3dc`, an
`engine.py` fix committed 37 seconds ahead of this card's filing commit
`dc484d63`. At `6d36c3dc^`, `:5237` is `_cmd_status`'s `_git_auto_commit`
call, `:5710` `_cmd_advance`'s and `:5426` `goc new --commit`'s
`commit_targets`. In the filing commit's own tree, each number is a `print`
six lines earlier. The 2026-08-10 hygiene pass anchored the cites there, and
every pass since has tracked those `print` lines.

Re-anchored by the prose, matching the staleness re-check above:
`5234-5237` → `6854-6857` (`commit_targets = [card_dir]` … the
`_git_auto_commit` call), Option A's `engine.py:6851` → `:6857`, and
`_cmd_unadvance`'s `:5725` → `:7463` in § Location and Option A. Recorded as
the second instance on
`citation-repair-pass-moves-correct-cites-when-a-parallel-commit-lands-beside-the-card`.

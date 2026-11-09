## 2026-11-09T01:58:21Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/install.py:920`
(`if write.path.name == "log.md":`) and `goc/install.py:866`
(`writes.append(PlannedWrite("shared", "write", deck_dir / "log.md", "project-state"))`), both moved by `0be57d4d`.
Reproducer: `reproduce.py` → exit 1, "FAIL: `goc install` overwrote the authored deck journal (sentinel-less deck was treated as a fresh target)".
Verdict: still live. Re-anchored `goc/install.py:937-938` → `:1193-1194` (both occurrences; the skip now reads `if write.kind == "deck-log": continue`)
and `goc/install.py:883` → `:1015` (the journal's `PlannedWrite` in `_plan_writes`, now a three-line `writes.append(...)` at `:1014-1016`).
Gate unchanged.

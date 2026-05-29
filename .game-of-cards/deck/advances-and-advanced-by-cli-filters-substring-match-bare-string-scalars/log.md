## 2026-05-29T06:20:28Z — Closure

- **What changed**: `goc/engine.py:1949-1962` — `filter_cards` guards the `advances` / `advanced_by` membership tests with `isinstance(..., list)`, matching the walker-fix family (`dependency_blockers`, `compute_values`, supersedes cycle walkers, `tags` property).
- **Verification**: `reproduce.py` exits 0 (`substring foo matched: []`); regression suite 201/201 green; plugin mirrors re-synced (`engine.py` propagated to claude/codex/openclaw).
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 201 passed / 0 failed / 0 xfailed

## Closure verification (2026-05-29T06:20:42Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

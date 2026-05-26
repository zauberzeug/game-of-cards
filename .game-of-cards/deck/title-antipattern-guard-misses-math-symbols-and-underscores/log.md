## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/engine.py:3537-3538` — added two `TITLE_ANTIPATTERNS` rows (math/symbol-or-non-ASCII `[^a-zA-Z0-9\s_-]`, and bare underscore `_`) so the guard fires its tailored message before the regex gate; `goc/templates/skills/card-schema/SKILL.md:759` — added the matching Underscores doc row so the table and code agree row-for-row (8 rows each).
- **Verification**: `goc new "late-hr-≥-half"` and `goc new "my_first_card"` now print tailored antipattern messages naming the remedy, not the bare regex error; `_check_title_antipatterns` returns a non-empty list for both.
- **Audit**: PASS — no project rubric configured; mechanical fix (doc/code reconciliation of an existing UX contract).
- **Project impact**: n/a
- **Tests**: no pytest suite; `uv run goc validate` clean, `python scripts/sync_plugin_assets.py --check` green.

## Closure verification (2026-05-26T23:10:57Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present

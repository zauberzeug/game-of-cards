## 2026-06-12T04:50:11Z — Closure

- **What changed**: AGENTS.md:259-265 — the "deliberately omits" sentence now names only `templates/skills/` and states the hook templates ARE shipped (the bundled engine derives its hook list from `templates/hooks/*.py`), matching `scripts/sync_plugin_assets.py:69-71`'s docstring and the on-disk deep mirrors.
- **Verification**: `grep -n "deck_prompt_router.*hook templates" AGENTS.md` → no match (exit 1); `python scripts/sync_plugin_assets.py --check` → exit 0; `uv run goc validate` → exit 0.
- **Audit**: PASS — no rubric configured; mechanical fix (doc realigned to code; the code-side behavior was deliberate per commit 8277962).
- **Project impact**: n/a
- **Tests**: not run (doc-only change; sync --check + goc validate green)
- **Bundled with**: n/a

## Closure verification (2026-06-12T04:50:12Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 2/2 ticked
- [x] log-md-closure-entry — '## 2026-06-12 — Closure' present

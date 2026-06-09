## 2026-06-09T06:48:55Z — Closure

- **What changed**: `goc/install.py`, `scripts/sync_plugin_assets.py`, `goc/templates/bootstrap/_goc-bootstrap.sh`, `goc/templates/skills/codex-kickoff/SKILL.md`, `codex-plugin/README.md` — Codex-rendered skills now carry a command resolver and the Codex plugin payload ships `skills/_goc-bootstrap.sh`, which invokes the sibling bundled `bin/goc` wrapper.
- **Verification**: Added downstream-style bootstrap regression with no `goc` on `PATH`; full regression suite passed.
- **Audit**: PASS — no project rubric configured; mechanical fix.
- **Project impact**: Codex plugin-only downstream users get an explicit no-global-shim path to the bundled GoC engine.
- **Tests**: 410 passed / 0 failed / 1 skipped; `uv run goc validate` passed.

## Closure verification (2026-06-09T06:49:39Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-09 — Closure' present

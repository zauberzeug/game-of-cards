## 2026-05-19T17:04:24Z — Closure

- **What changed**: `goc/engine.py:2529-2574` — `_claude_plugin_present()` replaced its 2-level nested loop with an `rglob('game-of-cards*')` walk that accepts `skills/` as direct child or grandchild, covering the modern `cache/<marketplace>/<plugin>/<version>/skills/` layout. Fix landed in commit 18587fd alongside the card file (the card was filed *with* the fix; this closure ratifies it after verification).
- **Verification**: `uv run python .game-of-cards/deck/plugin-auto-detection-misses-versioned-marketplace-paths/reproduce.py` exits 0 — all 5 cases pass (versioned, 2-level, direct, no-payload, symlink-loop). `uv run goc validate` clean.
- **Audit**: PASS — no rubric configured; mechanical fix (auto-detect predicate broadening).
- **Project impact**: n/a
- **Tests**: reproduce.py 5/5 pass; no pytest suite in this repo.

## Closure verification (2026-05-19T17:04:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-05-19 — Closure' present

## 2026-05-30T21:40:20Z — Closure

- **What changed**: `goc/install.py` — `_strip_goc_settings_entries` now snapshots events that were already empty before the strip pass and skips them during the post-strip cleanup, preserving user-authored placeholder events.
- **Verification**: `uv run python .game-of-cards/deck/goc-upgrade-cleanup-deletes-user-authored-empty-hook-event-lists/reproduce.py` exits 0; full suite 334/334 passing.
- **Audit**: PASS — no principle touched, mechanical fix (snapshot pre-strip empties, skip during cleanup; preserves the documented user-data preservation contract).
- **Project impact**: n/a
- **Tests**: 334 passed / 0 failed / 0 xfailed
- **Bundled with**: —

## Closure verification (2026-05-30T21:40:39Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present

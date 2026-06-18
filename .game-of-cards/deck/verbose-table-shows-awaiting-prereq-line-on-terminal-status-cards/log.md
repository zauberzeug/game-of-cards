## 2026-06-18T05:30:00Z — Closure

- **What changed**: `goc/engine.py:2677` — gate the verbose-table `awaiting: ... (you may start)` advisory on `t.status not in TERMINAL_STATUSES`, mirroring the board renderer's `live` gate. Plugin mirrors (claude/codex/openclaw `goc/engine.py`) regenerated via `scripts/sync_plugin_assets.py`.
- **Verification**: reproduce.py exits 0 (was 1); the `done` card no longer shows `awaiting: prereq-open (you may start)` while a live card with the same open prereq still does.
- **Audit**: PASS — no principle touched, mechanical fix (single-renderer drift aligned to the shared `TERMINAL_STATUSES` liveness rule the board already encodes).
- **Project impact**: n/a
- **Tests**: 458 passed / 0 failed / 0 xfailed (new `tests/test_verbose_table_awaiting_liveness.py` covers all three terminal statuses + a live-card control).

## Closure verification (2026-06-18T05:29:54Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-18 — Closure' present

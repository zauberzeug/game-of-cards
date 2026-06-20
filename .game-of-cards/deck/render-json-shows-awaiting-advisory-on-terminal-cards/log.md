## 2026-06-20T05:00:00Z — Closure

- **What changed**: `goc/engine.py` `render_json` (~2764) — gate
  `awaiting` / `dependency_awaiting` on `status not in TERMINAL_STATUSES`,
  mirroring the table renderer's liveness guard. Plugin mirrors
  (`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`) regenerated via
  `scripts/sync_plugin_assets.py`.
- **Verification**: reproduce.py exits 0 (terminal cards report
  `awaiting=[]`, `dependency_awaiting=False`; live card keeps its
  advisory). Real-deck `goc --status all --json` now shows 0 terminal
  cards with a stale advisory (was 2: `provide-openclaw-plugin-for-skills-and-hooks`,
  `design-claim-protocol-with-branch-and-author-metadata`).
- **Audit**: PASS — no principle touched, mechanical fix (surface-parity
  guard mirroring an existing renderer gate).
- **Project impact**: n/a
- **Tests**: 463 passed / 0 failed (new `tests/test_json_awaiting_liveness.py`).
- **Bundled with**: n/a

## Closure verification (2026-06-20T04:40:12Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-20 — Closure' present

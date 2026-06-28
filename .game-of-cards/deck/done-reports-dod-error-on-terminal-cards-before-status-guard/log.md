## 2026-06-06T05:35:00Z — Closure

- **What changed**: `goc/engine.py` `_cmd_done` / `_cmd_done_bundle` — moved the terminal-status guards (`already done`, `in TERMINAL_STATUSES`) ahead of the DoD-completeness checks so a terminal card with unchecked DoD boxes is refused with the authoritative terminal-status message, not the misleading "unchecked DoD boxes" one.
- **Verification**: `reproduce.py` exits 0 (was 1); refusal now reads `status is 'disproved' (terminal)`. Two new regression tests in `tests/test_close_terminal_gate_guard.py` (single-card + bundle) pass.
- **Audit**: PASS — no principle touched, mechanical fix (guard-ordering correctness; restores the message contract of the closed card done-command-overwrites-terminal-cards).
- **Project impact**: n/a
- **Tests**: 397 passed / 0 failed / 0 xfailed (full suite, after plugin-mirror re-sync)

## Closure verification (2026-06-06T05:30:16Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-06 — Closure' present

## 2026-05-27T05:40:00Z — Closure

- **What changed**: `goc/engine.py:662-684` — `_is_iso_date` now parses the datetime shape with the same `strptime("%Y-%m-%dT%H:%M:%SZ")` the consumer uses, not just the `value[:10]` date prefix; comment updated to say so.
- **Verification**: reproduce.py exits 0 — `_is_iso_date('2026-05-20T25:61:99Z')` → False; `waiting_impedes` → True (no raise). Valid `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SSZ` shapes still parse/impede unchanged.
- **Audit**: PASS — no principle touched, mechanical fix (validator-matches-parser calendar check; same shape as the closed date-prefix sibling).
- **Project impact**: n/a
- **Tests**: 158 passed / 0 failed (after plugin-mirror re-sync of engine.py into claude/codex/openclaw payloads).

## Closure verification (2026-05-27T05:35:29Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

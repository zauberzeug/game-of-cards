## 2026-07-16T01:11:29Z — Closure

- **What changed**: scripts/set_cadence.py:219 — epilog day-cap `(<=31)` → `(<=30)`, matching the interval_to_cron guard.
- **Verification**: reproduce.py exit 0 — `interval_to_cron('30d') -> '13 0 */30 * *'`.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: full suite green (728 collected + 2 new boundary tests from the sibling closure this session).

## Closure verification (2026-07-16T01:11:38Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 2/2 ticked
- [x] log-md-closure-entry — '## 2026-07-16 — Closure' present

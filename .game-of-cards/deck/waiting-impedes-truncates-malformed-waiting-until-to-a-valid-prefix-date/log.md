## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `waiting_impedes` (~1660) and `validate_waiting_overlay` (~1378) — gate the `waiting_until` parse on `_is_iso_date` (full-string anchored shape + calendar parse) before calling `_date_part`/`fromisoformat`, so a prefix-valid-but-malformed value like `2026-05-20xx` no longer truncates to a parseable past date. `waiting_impedes` now routes such a value into the `until_unparseable=True` branch (impedes); `validate_waiting_overlay` skips it (the malformed shape is surfaced by the main frontmatter validator, not re-reported here).
- **Verification**: reproduce.py exits 0 (prefix-garbage `impeded=True`, matching total-garbage and bare-reason controls). 11-case regression matrix across `waiting_impedes` (valid date-only/datetime-UTC future+elapsed, bare future/elapsed, bare-reason, no-overlay, prefix/total garbage) and 4-case `validate_waiting_overlay` matrix: all pass, no behavior change for valid inputs.
- **Audit**: PASS — invokes the read-time-guard-mirrors-validator principle (a read-time guard must not accept input the frontmatter validator rejects); the anchored `_is_iso_date` predicate is now the shared contract between `goc validate` and the queue-visibility guards.
- **Project impact**: n/a
- **Tests**: no pytest suite; `goc validate` rc=0 after plugin-mirror sync. reproduce.py + ad-hoc regression matrix green.
- **Bundled with**: n/a

## Closure verification (2026-05-27T03:23:39Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

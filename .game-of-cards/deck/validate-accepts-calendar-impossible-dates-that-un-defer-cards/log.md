## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `_is_iso_date` (~line 662) now parses the date portion with `date.fromisoformat` after the regex shape check, so the validator predicate matches the consumer's parser; `waiting_impedes` (~line 1644) treats a present-but-unparseable `waiting_until` as still-impeding (read-time backstop); three date-error messages reworded "not a valid ISO … date".
- **Verification**: reproduce.py exit 0 — `_is_iso_date('2026-13-45')` → False, `waiting_impedes(bare, '2026-13-45')` → True, valid-date/datetime controls green; `validate_card` emits a `waiting_until`/`created` error for calendar-impossible inputs and none for valid ones; full `goc validate` clean (no ERRORs).
- **Audit**: PASS — no project rubric configured (finish-card hook empty); correctness fix restoring the predicate==parser invariant.
- **Project impact**: n/a
- **Tests**: no pytest suite; reproduce.py + ad-hoc validate_card checks pass
- **Bundled with**: none

## Closure verification (2026-05-27T02:20:08Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

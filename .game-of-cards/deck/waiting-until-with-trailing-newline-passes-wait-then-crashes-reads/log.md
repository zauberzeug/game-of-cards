## 2026-07-22T02:10:00Z — Closure

- **What changed**: `goc/engine.py` — `_ISO_DATE_RE` / `_ISO_DATETIME_UTC_RE` now anchor with `\Z` instead of `$`, and `_is_iso_date` calendar-parses the full string value instead of the `_date_part` truncation, so the predicate rejects exactly what the consumers reject.
- **Verification**: `reproduce.py` prints `[OK] defect no longer fires` (wait exits 2 on `'2026-08-01\n'`); new `tests/test_iso_date_trailing_newline.py` — 6 tests covering predicate rejection, the `_waiting_until_instant` None backstop, `validate_card` FAIL on a stored value, and `validate_waiting_overlay` not crashing.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: third instance of the waiting_until predicate/parser mismatch family closed; sibling `$`-anchor defect on titles filed separately as trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir.
- **Tests**: 752 passed / 0 failed

## Closure verification (2026-07-22T01:56:53Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-22 — Closure' present

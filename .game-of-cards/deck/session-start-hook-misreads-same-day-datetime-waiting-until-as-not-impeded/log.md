## 2026-05-29T09:58:17Z — Closure

- **What changed**: `goc/templates/hooks/deck_session_start.py:85-145` — `_is_impeded` now parses `waiting_until` into a UTC instant via a new `_parse_waiting_until` helper that mirrors `engine._waiting_until_instant`, then compares at full timestamp precision instead of truncating to date. The OpenClaw TypeScript port (`openclaw-plugin/index.ts:120-160`) was updated in lockstep: `parseIsoDate` (UTC-midnight only) is gone, replaced by `parseWaitingUntil` returning a `Date` for both bare-date and `Z`-suffixed datetime shapes; the misleading "matches the Python hook's date-level coarseness" comment was removed and the comment now cites the engine contract being mirrored. The misleading docstring claim that "a date-level comparison suffices" was corrected to call out the same-day-future datetime cell as the counterexample.
- **Verification**: pre-fix `reproduce.py` showed Cases A and C diverged (hook said not-impeded, engine said impeded) on `<today>T23:59:59Z`; post-fix all three cells agree (`DIVERGED: False` on every case). New regression test `test_same_day_future_datetime_waiting_until_is_impeded` in `tests/test_session_start_hook.py` pins `datetime.now` to a fixed UTC instant via a `FrozenDateTime` subclass, then asserts `_is_impeded` returns True for `<today>T23:59:59Z` and False for `<today>T00:00:00Z` so the boundary case does not rot at midnight.
- **Audit**: PASS — no principle touched, mechanical fix (cross-implementation parity bug; the engine contract is already documented and unchanged).
- **Project impact**: n/a
- **Tests**: 226 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`). `uv run goc validate` is OK across the deck.
- **Bundled with**: none

## Closure verification (2026-05-29T09:58:37Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 closed
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

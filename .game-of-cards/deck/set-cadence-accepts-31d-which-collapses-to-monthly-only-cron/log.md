## 2026-07-09T01:50:00Z — Closure

- **What changed**: `scripts/set_cadence.py` — day-interval guard tightened from `n > 31` to `n > 30`, with the error message and docstring restated for the 1 ≤ N ≤ 30 range and the day-1-collapse rationale (`*/N` with N ≥ 31 matches only the 1st). `tests/test_set_cadence.py` — `test_day_interval_over_31_rejected` became `test_day_interval_over_30_rejected` (adds "31d" to the rejected set); `test_day_interval_boundary_31_supported` became `test_day_interval_boundary_30_supported` asserting `30d → 0 0 */30 * *`.
- **Decision**: rubric-derived (no gate raised) — the predecessor card's recorded principle ("a spec whose `*/N` step can only match day 1 silently collapses to monthly and must raise ValueError") applies verbatim to N = 31; see the README's "Decision (rubric-derived)" section.
- **Verification**: `reproduce.py` exits 0 (`interval_to_cron("31d", 13)` raises ValueError); `tests.test_set_cadence` 20/20; full suite 704 passed.
- **Audit**: PASS — mechanical off-by-one bounds fix mirroring the predecessor's own rationale; no principle touched.
- **Project impact**: `tune-cadence` / `set_cadence.py` callers asking for `31d` now get an explicit rejection instead of a silent first-of-month-only schedule.
- **Bundled with**: post-close amendment of [set-cadence-day-interval-over-31-emits-monthly-only-cron](../set-cadence-day-interval-over-31-emits-monthly-only-cron/) (forward pointer per "closure is not frozenness").

## Closure verification (2026-07-09T01:44:10Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-07-09 — Closure' present

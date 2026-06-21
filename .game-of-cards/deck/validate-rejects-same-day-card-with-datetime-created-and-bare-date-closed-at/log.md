## 2026-06-21T04:46:16Z — Closure

- **What changed**: `goc/engine.py` — the cross-field `closed_at >= created` ordering check in `validate_card` (~line 1429) now compares at day granularity when either operand is a bare date, instead of promoting bare dates to midnight UTC and comparing strictly. Added the `_is_date_only` helper next to the other ISO helpers (~line 861). A same-day card with a datetime `created` and a bare-date `closed_at` no longer trips a spurious `closed_at predates created` error; genuine inversions (earlier `closed_at` day, both-datetime intra-day reversal) still fire.
- **Verification**: `reproduce.py` exits 0 (same-day mixed-granularity in both directions accepted; earlier-day bare-date close and both-datetime intra-day inversion still rejected). 3 new cases added to `tests/test_validate_closed_at_ordering.py` (now 8 tests, all pass).
- **Audit**: PASS — no principle touched. Narrows an over-broad check introduced by the predecessor `validate-accepts-closed-at-that-predates-created`; the absolute invariant (creation precedes closure) is preserved at the only granularity actually known.
- **Project impact**: n/a — false positive would only surface on hand-edited / `goc migrate`-imported cards carrying a bare-date `closed_at`; the engine happy path writes full datetimes for both stamps.
- **Tests**: 475 passed / 0 failed (full suite); plugin mirrors re-synced via `scripts/sync_plugin_assets.py`.
- **Bundled with**: (none — surfaced via audit while the ready queue was empty)

# Log

## 2026-06-24 — filed and fixed (pull-card session)

Surfaced by an audit-deck hunt while the pull queue was empty
(every `human_gate: none` open card carried an active `waiting_on`
overlay). Confirmed the `ACTIVE:` banner at `goc/engine.py:3477`
passed the full unfiltered deck to `render_active_notice`, ignoring
`--worker`, while the board branch at line 3463 already honored it.

Fix-through (gate-free, single-site): scoped `notice_cards` to
`--worker` using the same `_worker_who` match `filter_cards` uses, so
the banner mirrors the board on the identical flag. Scope limited to
`--worker` deliberately — extending the banner to `--tag` /
`--contribution` / `--human-gate` is a separate, debatable call left
out of scope.

Evidence: `reproduce.py` drives the real CLI against a temp deck
(`alice-active`, `bob-active`, `alice-open`); fails on the unfixed
engine (banner lists bob), passes after the fix. Regression coverage
in `tests/test_active_notice_worker_scope.py` (worker-scoped banner +
unfiltered banner still lists all active cards). Full suite green;
plugin mirrors re-synced via `scripts/sync_plugin_assets.py`.

# Log

## 2026-06-27 — closed (done)

Fixed the active-card banner's near-term-flow tiebreak undercounting
downstream flow under `--worker`. `render_active_notice` now accepts an
optional full-deck `by_title` (mirroring `render_leverage_line` /
`render_table` / `render_board`) and threads it into `sort_default`;
`_cmd_default` passes `full_by_title`. Without it, the worker-scoped
subset handed to the banner dropped downstream cards owned by other
workers, collapsing equal-value active cards to the oldest-first
`created` tiebreak.

Root cause: the closed card
`scheduler-tiebreak-undercounts-downstream-flow-through-filtered-out-cards`
(2026-06-07) gave `sort_default` a `by_title` param but never added one
to `render_active_notice` — it relied on the call site passing the full
deck. `active-card-banner-ignores-worker-filter` (2026-06-24) then made
that call site pass a worker subset, silently re-introducing the bug on
this one path.

- `goc/engine.py`: `render_active_notice` gains `by_title=`; `_cmd_default`
  threads `full_by_title`. Plugin mirrors re-synced.
- `reproduce.py`: exits 0 post-fix (a1 with two live downstream ranks
  ahead of older a2 with one), exited 1 before.
- `tests/test_active_notice_worker_scope.py`:
  `test_worker_banner_tiebreak_counts_full_deck_live_flow` regression.

Full suite green (623 tests), `goc validate` clean, plugin mirror parity OK.

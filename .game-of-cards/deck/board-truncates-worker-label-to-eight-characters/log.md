# Log

## 2026-06-07 — closed (done)

Dropped the `who[:8]` slice in `render_board.card_cell` (`goc/engine.py`)
so the worker label renders in full. Columns already auto-size to their
widest rendered cell (the contract `board-active-card-worker-label-not-truncated`
established for the title), so the full identifier widens its column
rather than overflowing — no grid breakage.

- `reproduce.py` now exits 0: `@claude[bot]` renders in full instead of
  `@claude[b`.
- Added regression `tests/test_board.py::test_board_renders_full_worker_label_over_eight_chars`
  (worker `claude[bot]` → asserts `@claude[bot]` present, `@claude[b ` absent).
- Plugin engine mirrors (claude/codex/openclaw) regenerated via
  `scripts/sync_plugin_assets.py`.
- Full suite green (398 tests).

Found via an audit pass when the pull queue was empty (all `human_gate: none`
open cards carried active `waiting_on` overlays). Dogfood note: the card's
own auto-stamped `worker.who: claude[bot]` was itself a live instance of the
bug on the board.

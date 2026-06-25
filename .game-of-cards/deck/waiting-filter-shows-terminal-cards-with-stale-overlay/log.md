# Log

## 2026-06-25 — filed and fixed (fix-through)

Surfaced during an audit-deck sweep when the pull queue was empty.

**Defect:** the `--waiting` filter (`engine.py:3499`) applied
`waiting_impedes(t)` with no terminal-status gate, while `--waiting`
auto-extends the status scope to `all`. Because closing a card never
clears its `waiting_on` / `waiting_until` overlay (a documented
invariant), a closed-but-deferred card leaked into the impeded view.
This was the lone un-gated read-view: board (`card_cell`'s `live`),
`card_is_ready`, `card_is_workable_for_scheduler`, and the gated-leverage
line all already gate the overlay on non-terminal status.

**Fix:** gated the filter on `t.status not in TERMINAL_STATUSES`,
mirroring the board renderer's `live` guard, with a comment naming the
shared semantics so the two human-facing views cannot drift apart.

**Evidence:** `reproduce.py` drives the real `goc --waiting --json`
against a temp deck — before the fix it showed `closed-but-still-deferred`
(done); after, only `open-impeded`. Added a regression in
`tests/test_waiting_filter_status_scope.py`
(`test_waiting_excludes_terminal_cards_with_stale_overlay`) exercising
done/disproved/superseded while asserting open/active impeded cards still
surface. Full suite (591 tests) green; `goc validate` clean. Plugin
mirrors regenerated via `scripts/sync_plugin_assets.py`.

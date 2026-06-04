# Log

## 2026-06-04 — closed (done)

`render_board` sliced each status column to `max_rows` (default 20) with
no overflow indicator, unlike every other capped list in the tool
(`render_active_notice`, the tag-sample renderer, the validate report).
On a 90-open-card deck the OPEN column showed 20 rows and silently hid 70.

Fix (`goc/engine.py`, `render_board`): capture each column's pre-slice
length, and when it exceeds `max_rows` append a synthetic final cell
`… +N more` to that column before `col_widths` is computed, so the
indicator participates in width sizing and the grid stays aligned.

Tests (`tests/test_board.py`): added three cases — truncated column
advertises `+N more` with the correct hidden count; a column at/below the
cap emits no false `+0 more`; the indicator row keeps every rendered row
the same display width. `reproduce.py` now exits 0. Plugin engine mirrors
re-synced. `goc validate` clean; full suite (378 tests) green.

Surfaced by an audit-deck renderer sweep and fixed through in the same
session. Distinct from the closed `negative-board-row-limit-hides-cards`
(that rejected negative `--max-rows`; this surfaces the default positive cap).

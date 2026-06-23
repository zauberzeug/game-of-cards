---
title: verbose-table-shows-awaiting-prereq-line-on-active-cards
status: active
stage: null
contribution: medium
created: "2026-06-23T08:53:29Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — the verbose table omits the `awaiting: ... (you may start)` line for an `active` card with an open `advanced_by` prereq, while still showing it for an `open` card with the same prereq.
  - [ ] TDD: a regression test asserts the table and board agree on the dependency advisory for an active card (table omits the awaiting line; board omits the `⏳`).
  - [ ] MECHANICAL: the existing terminal-status liveness test (`tests/test_verbose_table_awaiting_liveness.py`) still passes unchanged.
  - [ ] `uv run goc validate` passes.
  - [ ] `uv run python -m unittest discover -s tests` passes.
worker: {who: "claude[bot]", where: main}
---

# Verbose table shows the "you may start" advisory on active cards

## Location

`goc/engine.py:2767-2769` (the verbose `render_table` dependency
advisory), contrasted with `goc/engine.py:2925-2929` (the `render_board`
not-ready gate).

## What's broken

The verbose table renders the dependency advisory for any card the
shared `dependency_advisory` helper considers live — i.e. any
non-terminal card:

```python
# goc/engine.py:2767
blockers, _ = dependency_advisory(t, by_title)
if blockers:
    out_lines.append(f"    awaiting: {', '.join(blockers)} (you may start)")
```

`dependency_advisory` gates **only** on terminal status (it returns
`([], False)` for `done`/`disproved`/`superseded`, else the live
blockers). So an **active** card with a non-terminal `advanced_by`
prereq prints `awaiting: <prereq> (you may start)`.

The board renderer applies a **stricter** gate for the same signal —
its own documented open-only slice:

```python
# goc/engine.py:2925
not_ready = live and (
    t.human_gate != "none"
    or (t.status == "open" and dependency_advisory(t, by_title)[1])  # open-only
    or waiting_impedes(t)
)
```

The board's comment (lines 2922-2924) states it "additionally flags
only open ones." So an active card with an open prereq gets the
table's `awaiting … (you may start)` line but **no** `⏳` on the board.

Two defects in one site:

1. **Renderer drift.** The table and board — both human-facing
   surfaces — disagree on whether an active card's open prereq is
   surfaced. This is exactly the renderer-drift class this repo
   already tracks (`renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift`),
   except that closed meta-fix centralized only the *terminal* gate;
   the board's later *open-only* refinement was never mirrored into
   the table.
2. **Wrong call-to-action.** `(you may start)` is a pull-queue hint —
   it tells a puller "this has an open prereq but you can still pull
   it." On an `active` card the work is already claimed and underway,
   so the hint has no audience and reads as nonsense.

## Empirical evidence

`reproduce.py` builds an open prereq, an `active` card depending on it,
and an `open` card depending on it, then renders both surfaces:

```
=== TABLE (verbose) ===
active-dep   active  ...
    awaiting: prereq-open (you may start)      <-- BUG: on an active card
open-dep     open    ...
    awaiting: prereq-open (you may start)
prereq-open  open    ...

=== BOARD ===
OPEN              | ACTIVE          | ...
open-dep [m] ⏳   | active-dep [m]  |    <-- board omits the marker for the active card
prereq-open [m]   |                 |
```

The board correctly suppresses the marker on `active-dep`; the table
does not.

## Why it matters

Reachability: the verbose table is produced by `render_table` on every
`goc -v` / `goc --verbose` invocation (the default human queue view at
verbosity ≥ 1). Any deck with an active card that carries a
non-terminal `advanced_by` edge — a routine shape once an in-progress
card depends on another — renders the misleading line. The two
human-facing renderers (table and board) then describe the same card
differently, which is precisely the drift the centralized
`dependency_advisory` helper exists to prevent.

## Fix

Gate the table's awaiting line on `t.status == "open"`, mirroring the
board's documented open-only slice:

```python
blockers, _ = dependency_advisory(t, by_title)
if t.status == "open" and blockers:
    out_lines.append(f"    awaiting: {', '.join(blockers)} (you may start)")
```

This aligns the two human-facing renderers and removes the meaningless
"(you may start)" from active cards. The existing terminal-status
liveness gate in `dependency_advisory` is preserved (terminal cards
still return no blockers), so the closed terminal-card regression keeps
passing.

The JSON renderer (`render_json`, lines 2847-2852) intentionally stays
out of scope: it is a machine surface that exposes the raw
`dependency_awaiting` advisory alongside a separate, status-gated
`ready` field, so a consumer combines the signals itself. The
open-only slice is a *human-renderer* concern shared by the table and
the board, not the JSON contract.

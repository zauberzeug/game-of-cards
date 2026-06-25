---
title: waiting-filter-shows-terminal-cards-with-stale-overlay
summary: "`goc --waiting` applies `waiting_impedes(t)` (engine.py:3499) with no terminal-status gate, while auto-extending the status filter to `all` (engine.py:3459). A closed card whose `waiting_on`/`waiting_until` overlay was never cleared on close (a documented invariant) therefore appears in the impeded view, which is meant to surface only active impediments. Every other read-view (board, verbose table, scheduler, ready/workable predicates) already gates the overlay on non-terminal status; this CLI filter is the lone un-gated site."
status: done
stage: null
contribution: medium
created: "2026-06-25T13:59:56Z"
closed_at: "2026-06-25T14:04:56Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — `goc --waiting` no longer lists a closed card that carries a stale overlay.
  - [x] TDD: a unittest under `tests/` asserts `goc --waiting` excludes terminal-status cards with an overlay while still surfacing open/active impeded cards (the live-card contract from `test_waiting_filter_status_scope.py` is preserved).
  - [x] MECHANICAL: the `--waiting` filter at `engine.py:3499` gates on `t.status not in TERMINAL_STATUSES`, mirroring the board renderer's `live` guard, with a comment naming the shared semantics.
  - [x] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
worker: {who: "claude[bot]", where: main}
---

# `goc --waiting` lists terminal cards that carry a stale impediment overlay

## Location

- Filter (un-gated): `goc/engine.py:3498-3499`
- Status auto-extension to `all`: `goc/engine.py:3459-3467`
- Authoritative predicate: `goc/engine.py:2253` (`waiting_impedes`)
- The established precedent the fix mirrors: board renderer `live`
  guard at `goc/engine.py:2982-2986`

## What's broken

`--waiting` is the impeded-cards view — it should surface cards a human
should act on because they are blocked *now*. Its filter runs the
authoritative impedance predicate but never gates on progress status:

```python
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if waiting_impedes(t)]
```

`--waiting` also auto-extends the default status filter to `all`, so
terminal cards are in scope before the filter runs:

```python
status = (
    "all"
    if (
        closed_since_threshold is not None
        or getattr(args, "waiting", False)
        or args.board
    )
    else "open"
)
```

`waiting_impedes` returns `True` for any card with a `waiting_on` reason
or a future `waiting_until`, regardless of status. Closing a card never
clears its overlay — this is a documented, deliberate invariant (see the
done cards `goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard`
and `board-paints-impediment-marker-on-terminal-cards-with-stale-overlay`).
So a card that was deferred and then closed carries a *stale* overlay
forever, and `--waiting` surfaces it as though it were an active wait.

Every other read-view already gates the overlay on non-terminal status:

- board renderer (`engine.py:2982-2986`): `not_ready = live and (... or waiting_impedes(t))`, where `live = t.status not in TERMINAL_STATUSES`
- `card_is_ready` (`engine.py:2219-2224`): returns `False` for any non-open card before consulting the overlay
- `card_is_workable_for_scheduler` (`engine.py:2244-2248`): returns `False` for terminal cards first
- gated-leverage line (`engine.py:3059-3063`): scoped to `t.status == "open"`

The `--waiting` CLI filter at line 3499 is the lone un-gated read-view.
The closed sibling `board-paints-impediment-marker-on-terminal-cards-with-stale-overlay`
fixed exactly this leak for the board; this card finishes the same sweep
for the table filter.

## Empirical evidence

`reproduce.py` builds a temp deck with a `done` card carrying
`waiting_on: external` + a future `waiting_until`, plus a live
`open-impeded` card, then runs the real `goc --waiting --json`:

```
Cards shown by `goc --waiting`: [('closed-but-still-deferred', 'done'), ('open-impeded', 'open')]
BUG CONFIRMED -- terminal cards in impeded view: ['closed-but-still-deferred']
```

The closed card leaks into the impeded view. After the fix the
reproducer prints `OK -- impeded view shows only live cards: ['open-impeded']`
and exits 0.

## Why it matters

The reachability path is fully through shipping verbs: `goc wait <card>
--reason external --until <future>` sets the overlay, then `goc done`
(or `goc status <card> disproved|superseded`) closes the card without
clearing it. Any subsequent `goc --waiting` then mixes historical,
non-actionable overlays into the human's "what is blocked right now"
view, inflating the impediment list and masking which waits actually
need attention. This is the same drift class the board and verbose-table
views were already hardened against — keeping the two human-facing
renderers from disagreeing about what counts as impeded.

This is distinct from the open card
`goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits`: that
card concerns the elapsed/bare-wait four-cell matrix (its proposed
switch to `waiting_impedes` is already in the tree at line 3499) and its
matrix never reasons about terminal status. The terminal gate is an
orthogonal axis.

## Fix

Gate the filter on non-terminal status, mirroring the board's `live`
guard so the two cannot drift:

```python
if getattr(args, "waiting", False):
    # `--waiting` surfaces *active* impediments. A terminal card can
    # still carry an overlay (closing never clears `waiting_on` /
    # `waiting_until`), but that overlay is stale by definition and is
    # not an actionable wait — mirror the board renderer's `live` gate.
    filtered = [
        t for t in filtered
        if t.status not in TERMINAL_STATUSES and waiting_impedes(t)
    ]
```

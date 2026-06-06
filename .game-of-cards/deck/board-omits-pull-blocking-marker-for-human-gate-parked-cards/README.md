---
title: board-omits-pull-blocking-marker-for-human-gate-parked-cards
summary: "`goc --board` paints no ⏳ marker on an open card parked behind `human_gate: decision`/`session`, so it reads as freely pullable when it is not. The board's `not_ready` predicate marks `dependency_blocked` (advisory) and `waiting_impedes` (hard block) but omits the third queue-hiding axis — `human_gate` — that both `card_is_ready` and `card_is_workable_for_scheduler` honor."
status: open
stage: null
contribution: medium
created: "2026-06-06T05:06:15Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py builds a deck with an open `human_gate: decision` card and a freely-pullable open card, renders the board, and asserts the gated card carries the ⏳ "not pullable" marker while the free card does not. Fails before the fix, passes after.
  - [ ] TDD: the existing impediment/dependency markers still render (no regression for `waiting_impedes` / `dependency_blocked` cards).
  - [ ] MECHANICAL: the board's `not_ready` predicate (`goc/engine.py:2668`) gains the `human_gate != "none"` axis so it is coupled to `card_is_ready` / `card_is_workable_for_scheduler`.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` green.
---

# board omits the pull-blocking marker for human-gate-parked open cards

## Location

`goc/engine.py:2667-2672` — the `not_ready` predicate inside `card_cell`
in `render_board`.

## What's broken

The board's per-cell renderer decides whether to paint the ⏳ "not
pullable / awaiting" marker:

```python
live = t.status not in TERMINAL_STATUSES
not_ready = live and (
    (t.status == "open" and dependency_blocked(t, by_title)) or waiting_impedes(t)
)
if not_ready:
    marker += " ⏳"
```

It gates the marker on only two of the three queue-hiding axes:
`dependency_blocked` (an advisory "you may start" prereq state) and
`waiting_impedes` (a hard impediment overlay). It **omits the third —
`human_gate`** — even though both authoritative queue predicates reject
a gated card:

```python
# card_is_ready (engine.py:1966-1972)
if card.status != "open":
    return False
if card.human_gate != "none":
    return False
if waiting_impedes(card):
    return False
return True
```

```python
# card_is_workable_for_scheduler (engine.py:1991-1997)
if card.status in TERMINAL_STATUSES:
    return False
if card.human_gate != "none":
    return False
if waiting_impedes(card):
    return False
return True
```

These two predicates carry an explicit coupling invariant — their
docstrings say "a future axis added here must be added there in the same
edit", enforced by `tests/test_scheduler_workable_predicate_coupling.py`.
The board's hand-rolled `not_ready` is a *third, uncoupled copy* of the
"is this card pullable" logic that drifted: it even marks the **weaker**
advisory state (`dependency_blocked` — which `card_is_ready` deliberately
treats as pullable) while skipping the **stronger** hard-block state
(`human_gate` — which both predicates reject). The result is backwards:
the board flags cards you *may* pull and stays silent on cards you *must
not*.

This is a distinct axis from the open card
[board-marks-pullable-and-impeded-cards-with-the-same-hourglass-glyph](../board-marks-pullable-and-impeded-cards-with-the-same-hourglass-glyph/),
which is about whether `dependency_blocked` and `waiting_impedes` should
*share* the ⏳ glyph. That is a UX taste call between two already-marked
states. This card is about a not-pullable state that gets **no marker at
all**. It is the exact sibling of the closed
[board-omits-marker-for-cards-with-active-waiting-overlay](../board-omits-marker-for-cards-with-active-waiting-overlay/),
which added ⏳ for the `waiting_impedes` axis — the same fix shape, one
axis over.

## Empirical evidence

```
card_is_ready(gated) = False
card_is_ready(free)  = True
--- board cells ---
'gated-decision [m]'         # human_gate: decision — NOT pullable, NO ⏳
'impeded [m] ⏳'             # waiting_on: external — not pullable, marked
'free [m]'                   # pullable
```

The `gated-decision` card is un-pullable (`card_is_ready` False) yet
renders identically to the freely-pullable `free` card, while the
equally-un-pullable `impeded` card is correctly marked. See
`reproduce.py`.

## Why it matters

The board (`goc --board`) is the primary at-a-glance human triage
surface. `human_gate: decision`/`session` is a first-class, common state
— `_cmd_triage` exists specifically to list gated cards, and the live
deck currently holds dozens of open cards behind a `decision`/`session`
gate. Every one of them renders on the board as though it were freely
pullable, defeating the board's purpose of showing what an autonomous
puller will and won't take. The reachability path is direct:
`_cmd_default` → `render_board` (engine.py:3149+) calls `card_cell` for
every card in every status column, including OPEN.

## Fix

Add the missing axis to the board's `not_ready` predicate so it is
coupled to `card_is_ready` / `card_is_workable_for_scheduler`, reusing
the existing ⏳ marker exactly as the closed waiting-overlay sibling did
(`human_gate` is an unambiguous "do not pull" signal, so it belongs with
the hard-block ⏳, not the glyph-distinction question of the other open
card):

```python
not_ready = live and (
    t.human_gate != "none"
    or (t.status == "open" and dependency_blocked(t, by_title))
    or waiting_impedes(t)
)
```

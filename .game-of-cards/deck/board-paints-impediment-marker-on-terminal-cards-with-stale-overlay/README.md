---
title: board-paints-impediment-marker-on-terminal-cards-with-stale-overlay
summary: "The kanban board (`goc --board`) paints the ⏳ impediment glyph on terminal (done/disproved/superseded) cards that still carry a `waiting_on`/`waiting_until` overlay. Closing a card never clears the overlay, and `card_cell` gates the dependency-block term on `status == \"open\"` but leaves the impediment term ungated — so a closed card renders as if it were still impeded, which is semantically impossible."
status: done
stage: null
contribution: medium
created: "2026-05-27T08:15:13Z"
closed_at: 2026-05-27T08:21:30Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits non-zero — no terminal-status card carries the ⏳ impediment marker on the board.
  - [x] MECHANICAL: the impediment term in `card_cell` (`goc/engine.py`) is gated so it only fires for non-terminal cards, mirroring the adjacent dependency-block term's `status == "open"` gate and `card_is_ready`'s status guard. The stored overlay fields are NOT mutated on close (preserved as historical record).
  - [x] PROCESS: the closed sibling `board-omits-marker-for-cards-with-active-waiting-overlay` is amended with a forward pointer to this card (dated log.md append).
worker: {who: "claude[bot]", where: main}
---

# Board paints the ⏳ impediment marker on terminal cards with a stale overlay

## Location

`goc/engine.py:2212` — the `card_cell` closure inside `render_board`.

## What's broken

The board's per-card marker predicate gates the *dependency-block* term on
`status == "open"`, but the *impediment* term (`waiting_impedes(t)`) is
ungated:

```python
not_ready = (t.status == "open" and dependency_blocked(t, by_title)) or waiting_impedes(t)
if not_ready:
    marker += " ⏳"
```

`render_board` renders all six columns including the terminal ones
(`done`, `disproved`, `superseded`, see `engine.py:2200`). Nothing clears
the impediment overlay when a card closes — `goc done`
(`done` command) and `goc status <t> disproved|superseded`
(`engine.py:3641`, which only sets `status` + `closed_at`) both leave
`waiting_on` / `waiting_until` in place. So a card that was impeded while
live keeps the overlay after closing, and `waiting_impedes(t)` returns
`True` for it — painting ⏳ in a terminal column.

A closed card cannot be impeded: the impediment overlay is the "can't
*pull* yet" signal, and a terminal card is never pullable. The
neighbouring dependency-block term already encodes this by gating on
`status == "open"`; `card_is_ready` (`engine.py`) likewise returns
`False` for any non-`open` card before it ever consults the overlay. The
impediment term was added to `card_cell` in the predecessor fix
[board-omits-marker-for-cards-with-active-waiting-overlay](../board-omits-marker-for-cards-with-active-waiting-overlay/)
without inheriting that status gate — this card is the follow-on gap.

## Empirical evidence

`reproduce.py` constructs three terminal cards — one clean `done`, one
`done` and one `disproved` each retaining a stale `waiting_on` — and
renders the board:

```
DONE                          | DISPROVED                          |
done-clean [m]                | disproved-with-stale-overlay [m] ⏳ |
done-with-stale-overlay [m] ⏳ |                                    |
------------------------------------------------------------
done-clean              has ⏳: False   (expected False)
done-with-stale-overlay has ⏳: True   (expected False)
disproved-stale-overlay has ⏳: True   (expected False)

DEFECT REPRODUCED: a terminal (closed) card is painted impeded (⏳).
```

The clean `done` card has no glyph; the two terminal cards with a leftover
overlay are wrongly marked impeded.

## Why it matters

The board is the primary human triage surface. The ⏳ glyph means "this
card is held — don't expect it to move." On a terminal card that reading
is false and confusing: a reviewer scanning the done/disproved columns
sees a closed item flagged as if it were still waiting on an external
dependency. It also undermines the glyph's signal elsewhere — once it
appears on closed cards, the eye stops trusting it on the open/active
cards where it actually matters.

## Fix

Gate the impediment term on non-terminal status, mirroring the adjacent
dependency term and `card_is_ready`:

```python
live = t.status not in TERMINAL_STATUSES   # or: t.status in {"open", "active"}
not_ready = live and (
    (t.status == "open" and dependency_blocked(t, by_title)) or waiting_impedes(t)
)
```

**Do not clear the overlay on close.** The stored overlay is a historical
record of why the card was held — the same way the `worker` field
persists after close (per AGENTS.md). The correct fix is the read-time
status gate in the renderer, not mutation of the stored fields at close
time. (`waiting_impedes` itself stays status-agnostic; callers that only
care about live cards apply the status gate, as `card_is_ready` already
does.)

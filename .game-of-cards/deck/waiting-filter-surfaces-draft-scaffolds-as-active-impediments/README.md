---
title: waiting-filter-surfaces-draft-scaffolds-as-active-impediments
summary: "`goc --waiting` lists `draft: true` scaffolds that carry a `waiting_on` overlay as actionable impediments, while the board renders the same card with the `✎` draft glyph and never the `⏳` impediment glyph. The `--waiting` post-filter gates on terminal-status and `waiting_impedes` but omits the `card_is_draft` exclusion that `card_cell` applies, so the two human-facing views disagree — contradicting the code comment that promises they cannot."
status: done
stage: null
contribution: medium
created: "2026-07-01T02:04:32Z"
closed_at: "2026-07-01T02:10:13Z"
human_gate: none
advances:
  - waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — a `draft: true` card carrying a `waiting_on` overlay does NOT appear in the `--waiting` filtered list
  - [x] TDD: the same draft renders `✎` (not `⏳`) on the board AND is absent from `--waiting`, so board and impeded-view agree (also covered by `tests/test_waiting_filter_status_scope.py::test_waiting_excludes_draft_scaffolds_with_overlay`)
  - [x] MECHANICAL: the `--waiting` post-filter at `engine.py:3698-3701` gains an `and not card_is_draft(t)` clause mirroring `card_cell`
  - [x] PROCESS: a non-draft card with an active overlay still appears in `--waiting` (no regression to the intended behavior)
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `goc --waiting` surfaces draft scaffolds as active impediments

## Location

`goc/engine.py:3698-3701` — the `--waiting` post-filter in `_cmd_default`.

## What's broken

The `--waiting` filter is documented to "mirror the board renderer's
`live` gate (`engine.py` `card_cell`) so the impeded view and the board
cannot disagree about what counts as impeded" (comment at
`engine.py:3695-3697`). But it only applies the terminal-status half of
the board's gate:

```python
# engine.py:3698-3701
filtered = [
    t for t in filtered
    if t.status not in TERMINAL_STATUSES and waiting_impedes(t)
]
```

The board's `card_cell` applies TWO exclusions before showing the `⏳`
impediment glyph — terminal-status AND draft:

```python
# engine.py:3138, 3150-3154
is_draft = live and card_is_draft(t)
...
not_ready = live and not is_draft and (
    t.human_gate != "none"
    or dependency_advisory(t, by_title, queue_only=True)[1]
    or waiting_impedes(t)
)
```

A `draft: true` scaffold is "not yet real work, not queueable"
(`card_is_draft`, `engine.py:2318`); it is hidden from the normal
queue, gets the `✎` marker (not `⏳`) on the board, and is excluded from
the scheduler. Only `--waiting` presents it as an actionable
impediment — the exact board/impeded-view divergence the comment claims
to prevent.

## Empirical evidence

`reproduce.py` output on a clean checkout (isolated scratch deck):

```
=== --waiting view ===
TITLE       STATUS  CONTR.  VALUE  GATE      TAGS  DOD
----------  ------  ------  -----  --------  ----  ---
freshdraft  open    medium    3.0  decision        0/1     <-- draft leaks in

=== normal queue === (empty — draft correctly hidden)

=== board ===
freshdraft [m] ✎       <-- ✎ draft glyph, NOT ⏳ impediment
```

The board says "draft, do not pull"; `--waiting` says "actionable
impediment." They disagree.

## Why it matters

Reachable entirely through shipping CLI verbs, no hand-editing:
`goc new <title>` stamps `draft: true` (`create-card` Step 4), and
`goc wait <draft> --reason external` sets the overlay without refusing a
draft. A human or agent triaging waits via `goc --waiting` then sees an
unpublished scaffold presented as blocked work. This is the sibling of
the closed `goc-triage-lists-unauthored-draft-scaffolds-as-parked-cards`
(which gave the `triage` verb its draft gate) and
`waiting-filter-shows-terminal-cards-with-stale-overlay` (which gave
`--waiting` its terminal gate). `--waiting` is the lone site that
received the terminal gate but never the draft gate.

## Fix (applied)

Added the draft exclusion to the `--waiting` comprehension at
`engine.py:3698-3706`, mirroring `card_cell` and `triage`:

```python
filtered = [
    t for t in filtered
    if t.status not in TERMINAL_STATUSES
    and not card_is_draft(t)
    and waiting_impedes(t)
]
```

The comment was updated to state the full board gate (terminal-status
AND draft). Regression covered by
`tests/test_waiting_filter_status_scope.py::test_waiting_excludes_draft_scaffolds_with_overlay`.

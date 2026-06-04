---
title: board-truncates-columns-to-max-rows-without-showing-how-many-are-hidden
summary: "`goc --board` caps each status column at `--max-rows` (default 20) by slicing the sorted card list, but emits no indicator when a column held more cards than were shown. On a deck with 90 open cards the OPEN column renders exactly 20 rows and silently hides the other 70 — the reader has no signal that the column is truncated."
status: open
stage: null
contribution: medium
created: "2026-06-04T05:12:17Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (a column truncated by --max-rows renders a "+N more" indicator naming the hidden count)
  - [ ] TDD: a column at or below the row cap renders no indicator (no false "+0 more")
  - [ ] TDD: the indicator count equals (column card total − rows shown) for the truncated column
  - [ ] MECHANICAL: the indicator row participates in column-width sizing so the grid stays aligned
  - [ ] `uv run goc validate` passes
---

# Board truncates columns to `--max-rows` without showing how many are hidden

## Location

`goc/engine.py:2590` (`render_board`):

```python
for c in columns:
    by_status[c] = sort_default(by_status[c], values=values)[:max_rows]
```

The slice caps each status column at `max_rows` (CLI default `20`, see
`engine.py:2766`). Nothing downstream records or displays the number of
cards that the slice dropped.

## What's broken

Every other place in the tool that caps a list surfaces the overflow.
`render_active_notice` appends `", +{len(active) - 3} more"`
(`engine.py:2687`); the tag-sample renderer appends `" (+{len(untagged)
- 3} more)"` (`engine.py:1818`); the validate report prints `"  ... and
{len(missing_summary) - 20} more"` (`engine.py:3404`). The board is the
lone exception: it slices and stays silent.

A reader running `goc --board` on a busy deck sees a full-looking column
and reasonably concludes that is the whole column. There is no glyph, no
footer, no count — the hidden cards are indistinguishable from
not-existing.

## Empirical evidence

On this repo's own deck (90 open cards):

```
$ uv run goc --status open | wc -l        # 90 open cards (+header rows)
$ uv run goc --board --no-color           # OPEN column renders exactly 20 rows
```

The OPEN column shows 20 cards and gives no indication that 70 more
exist. `reproduce.py` builds a 25-card open deck, renders with
`max_rows=5`, and asserts the truncated column carries a "+N more"
indicator. On the current renderer it fails:

```
FAIL: OPEN column hid 20 cards with no '+N more' indicator.
open cards filed       : 25
max_rows               : 5
non-empty OPEN rows     : 5
expected hidden count  : 20
'+20 more' present: False
```

## Why it matters

The board is the kanban view an operator scans to decide what to pull
and to gauge queue depth. Silent truncation makes a 90-deep queue look
20-deep — exactly the "no silent caps" failure the rest of the codebase
already guards against. The reachability path is direct: any invocation
of `goc --board` (or `goc --board --max-rows N`) on a deck where any
single status column holds more than `max_rows` cards triggers it; this
repo's own deck does so today.

This is distinct from the closed card
[negative-board-row-limit-hides-cards](../negative-board-row-limit-hides-cards/),
which rejected *negative* `--max-rows`. That fix validated the input;
this card is about the *default, positive* cap silently hiding rows.

## Fix

In `render_board`, capture each column's pre-slice length, and when it
exceeds the rows actually shown, append a synthetic final cell of the
form `… +N more` to that column's rendered cells (matching the existing
"+N more" convention). Because the indicator is added before
`col_widths` is computed from the rendered cells, it participates in
width sizing and the grid stays aligned.

---
title: negative-board-row-limit-hides-cards
summary: "`goc --board --max-rows -1` is accepted and slices cards out of each board column instead of rejecting the nonsensical negative row limit."
status: active
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] reproduce.py exits zero (negative max rows are rejected)
  - [ ] `goc --board --max-rows -1` exits with a concise Click validation error
  - [ ] Non-negative `--max-rows` values still render the board
  - [ ] `goc validate` passes after the option validation fix
---

# negative-board-row-limit-hides-cards

## Location

`goc/engine.py:858` declares `--max-rows` as an inferred integer option with
no range constraint.

## What's broken

The board renderer slices each status column with the user-provided value:

```python
by_status[c] = sort_default(by_status[c], values=values)[:max_rows]
```

Negative values are valid Python slice bounds, so `--max-rows -1` exits 0 and
silently drops the last card from each column instead of reporting bad input.

## Empirical evidence

`uv run goc --board --max-rows -1` exits 0 today and renders a board with rows
removed from the tail of each column.

## Why it matters

`--max-rows` is a display cap. Negative caps do not have a meaningful UI
interpretation, and accepting them makes the board look like cards vanished.

## Fix

Use Click's integer range validation so negative values fail as CLI usage
errors. Keep `0` and positive row caps working.

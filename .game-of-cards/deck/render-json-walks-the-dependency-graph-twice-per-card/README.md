---
title: render-json-walks-the-dependency-graph-twice-per-card
status: open
stage: null
contribution: low
created: "2026-06-21T19:06:47Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [api-contract]
definition_of_done: |
  - [ ] MECHANICAL: `render_json` computes `dependency_advisory(t, by_title)` once per card and unpacks the tuple, instead of calling it twice (`goc/engine.py:2811-2812`).
  - [ ] MECHANICAL: the emitted JSON is byte-for-byte unchanged (the two fields `awaiting` / `dependency_awaiting` keep the same values); `uv run goc validate` and the regression suite stay green; plugin mirrors synced.
---

# `render_json` walks the dependency graph twice per card

## Location

`goc/engine.py:2811-2812`, inside `render_json`.

## What's broken

`render_json` calls `dependency_advisory(t, by_title)` twice for the
same card — once to read each element of the returned tuple:

```python
"awaiting": dependency_advisory(t, by_title)[0],
"dependency_awaiting": dependency_advisory(t, by_title)[1],
```

`dependency_advisory` (`goc/engine.py:2108`) walks the card's
dependency edges; calling it twice per card doubles that walk on every
`goc --json` render. The tuple should be computed once and unpacked:

```python
blockers, awaiting = dependency_advisory(t, by_title)
...
"awaiting": blockers,
"dependency_awaiting": awaiting,
```

This is a clarity / efficiency cleanup, not a correctness defect — both
calls are pure and return the same value, so the JSON output is
identical. The neighbouring `render_table` (`engine.py:2727`) and
`render_board` (`engine.py:2880`) call sites already compute the
advisory once; only `render_json` double-walks.

## Why it matters

`goc --json` is the machine-readable interface other tooling consumes;
on a large deck the redundant per-card graph walk is wasted work and
the duplicated call obscures that the two JSON fields are two halves of
one advisory. Low contribution: no behavioural bug, purely a
walk-once cleanup that also reads clearer.

## Fix

Compute the advisory once and unpack, mirroring the table/board call
sites. No DoD test beyond confirming the emitted JSON is unchanged.

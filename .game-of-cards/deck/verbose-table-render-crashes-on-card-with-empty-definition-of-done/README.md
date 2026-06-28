---
title: verbose-table-render-crashes-on-card-with-empty-definition-of-done
summary: "`goc -vv` crashes with `AttributeError: NoneType has no attribute splitlines` on a card whose `definition_of_done:` key is present but empty, because the vendored YAML parser yields `None` and the `.get(..., '')` default only fires when the key is absent. This was the lone unguarded read of the field; every sibling read uses the `or ''` idiom. Fixed at `goc/engine.py:2460`."
status: done
stage: null
contribution: medium
created: "2026-06-03T04:37:18Z"
closed_at: "2026-06-03T04:40:07Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — building a `Card` with `definition_of_done: None` and calling `render_table([card], verbose=2, no_color=True)` returns a string instead of raising `AttributeError`.
  - [x] MECHANICAL: `render_table`'s `verbose >= 2` DoD read uses the established `or ""` guard (matching the sibling reads at engine.py:1814, 3187, 3273, and the `LIST_REL_FIELDS` loop just above it), so a `None` DoD renders as a blank block.
  - [x] PROCESS: a regression test lands in `tests/` asserting the `-vv` render survives a `None` DoD.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` stays green; `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc -vv` crashes on a card whose `definition_of_done` is empty

## Location

`goc/engine.py:2460-2461`, inside `render_table`'s `verbose >= 2`
detail block:

```python
dod = t.frontmatter.get("definition_of_done", "")
for line in dod.splitlines():
    out_lines.append(f"    {line.rstrip()}")
```

## What's broken

The `.get(..., "")` default only applies when the
`definition_of_done` key is **absent**. When a card's frontmatter
carries the key with an empty value (`definition_of_done:` on its own
line), the vendored YAML parser yields the key with value `None`, so
`.get(..., "")` returns `None` and `None.splitlines()` raises
`AttributeError: 'NoneType' object has no attribute 'splitlines'`.

This is the lone unguarded read of this field. Every sibling read
uses the `or ""` idiom precisely to absorb a `None`/non-string value:

- `goc/engine.py:1814` — `untagged_dod_items(... or "")`
- `goc/engine.py:3187`
- `goc/engine.py:3273` — `dod_text = fm.get("definition_of_done") or ""`

and the immediately-preceding `LIST_REL_FIELDS` loop in the same
block already uses `or []` for the same reason.

## Empirical evidence

`reproduce.py` builds a `Card` with `definition_of_done=None` and
calls `render_table` at three verbosity levels:

```
v0: renders OK
v1: renders OK
v2: AttributeError 'NoneType' object has no attribute 'splitlines'
```

A `None`-DoD card loads fine (`count_dod_boxes` treats a non-string
DoD as freeform `(0, 0)`) and renders fine at `-v` and on
`--board`; only the `-vv` detail block crashes. Because the renderer
crashes on the whole list, **one** malformed card blanks the entire
`goc -vv` queue view, not just its own row.

## Why it matters

Reachability path: the offending shape is a card with an empty
`definition_of_done:` line. The closed card
`validate-does-not-type-check-definition-of-done-...` made a
non-string DoD *fail `goc validate`*, but `validate` and the renderer
are independent code paths — a hand-edited card, a card authored
before that validate fix, or any deck where validate is not run on
every read still loads and participates in queues. `goc -vv` is a
routine queue-inspection command; it should degrade gracefully on a
loadable-but-malformed card, the way the sibling reads already do,
rather than taking down the entire detailed view.

## Fix

Replace line 2460 with the established guard:

```python
dod = t.frontmatter.get("definition_of_done") or ""
```

No design decision is involved — the intended behavior is
unambiguous and already established by the sibling call sites, and
this is the only remaining unguarded read of the field (no sibling
sweep outstanding).

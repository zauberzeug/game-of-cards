---
title: verbose-table-render-crashes-on-non-string-definition-of-done
status: done
stage: null
contribution: medium
created: "2026-07-03T01:30:45Z"
closed_at: "2026-07-03T01:37:24Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "`goc -vv` crashes with `AttributeError: 'list' object has no attribute 'splitlines'` on a card whose `definition_of_done:` parses to a YAML list (or any truthy non-string). The closed sibling swapped the read to the `or \"\"` idiom, but `or \"\"` only rescues *falsy* values — a truthy non-string passes straight through. Fix: coerce with `isinstance`, matching `count_dod_boxes`/`untagged_dod_items`."
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — `render_table` at `verbose=2` over a card whose `definition_of_done` is a `list` returns a string instead of raising `AttributeError`.
  - [x] TDD: a regression test in `tests/` asserts the `-vv` render survives a non-string (list) DoD, alongside the existing `None`-DoD test.
  - [x] MECHANICAL: the `verbose >= 2` DoD read uses an `isinstance(..., str)` guard, matching `count_dod_boxes`/`untagged_dod_items`.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` stays green; `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc -vv` crashes on a card whose `definition_of_done` is a non-string

## Location

`goc/engine.py:3012-3013`, inside `render_table`'s `verbose >= 2`
detail block:

```python
dod = t.frontmatter.get("definition_of_done") or ""
for line in dod.splitlines():
    out_lines.append(f"    {line.rstrip()}")
```

## What's broken

The closed sibling
[verbose-table-render-crashes-on-card-with-empty-definition-of-done](../verbose-table-render-crashes-on-card-with-empty-definition-of-done/)
replaced `.get(..., "")` with `.get(...) or ""` to absorb a `None`
DoD. But `or ""` only rescues *falsy* values. A **truthy non-string**
`definition_of_done` — a YAML block list (`definition_of_done:\n  -
a\n  - b`), a non-empty mapping, or a non-zero int — passes straight
through the `or ""` guard, and `list.splitlines()` raises
`AttributeError`.

Every *other* read of this field already guards on type, not
falsiness — `count_dod_boxes` (`engine.py:877`) and
`untagged_dod_items` (`engine.py:898`) both open with
`if not isinstance(dod_field, str): return ...`. The `-vv` render
path is the lone reader still using the falsy-only `or ""` idiom, so
it is the lone site that crashes on a truthy non-string.

## Empirical evidence

`reproduce.py` builds a deck with a card whose `definition_of_done`
is the YAML list `["- a", "- b"]` and drives the real CLI at three
verbosity levels:

Before the fix:

```
v0 (plain goc): renders OK (DoD shows "prose")
v1 (goc -v):    renders OK (DoD shows "prose")
v2 (goc -vv):   AttributeError: 'list' object has no attribute 'splitlines'
```

After the fix (`isinstance` coercion at the read site):

```
v0: renders OK
v1: renders OK
v2: renders OK

OK: all verbosity levels survived a non-string DoD.
```

Plain `goc` and `goc -v` survived even before the fix because they
read the DoD only through the type-guarded `count_dod_boxes`. `goc
validate` correctly flags the card (`definition_of_done: must be a
string`), but the read views must survive a validate-rejected card —
the same contract the empty-title / null-status / null-human-gate
closed cards established. Only `-vv` died.

## Why it matters

A non-string `definition_of_done` is reachable: a hand-authored or
one-shot-generated card can write `definition_of_done:` as a YAML
block list (the natural shape a human reaches for when listing DoD
items), and the vendored parser yields a Python `list`. Such a card
survives in the deck (plain `goc`, `goc -v`, and board all render it)
until someone runs `goc -vv`, at which point the *entire queue view*
crashes — not just the offending card's row. One malformed card takes
down the verbose read for the whole deck.

## Fix

Coerce the field to a string before calling `.splitlines()`, mirroring
the established `isinstance` guard in `count_dod_boxes`/`untagged_dod_items`:

```python
dod = t.frontmatter.get("definition_of_done")
if not isinstance(dod, str):
    dod = ""
for line in dod.splitlines():
    out_lines.append(f"    {line.rstrip()}")
```

Single site, no decision. (The frontmatter *emitter* has the same
falsy-only guard on this field — a separate, decision-adjacent
"coerce once at load vs. guard every consumer" question that is out
of scope for this mechanical read-path fix.)

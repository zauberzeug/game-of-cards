---
title: repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string
summary: "`find_half_edges` guards its OUTER walk against non-list `advances`/`advanced_by` but not the INNER `inverse_list` it pulls from the neighbour card. When the neighbour's inverse field is a hand-edited bare string, the `if t.title not in inverse_list` becomes a substring check — a substring hit silently passes a missing reverse edge. `goc repair-edges` then reports `No half-edges found.` for an asymmetric pair. Same root-cause family as the closed `compute-values-iterates-non-list-advances-character-by-character` fix; this is the unfixed inner-walker sibling."
status: done
stage: null
contribution: low
created: "2026-05-29T05:11:41Z"
closed_at: "2026-05-29T05:17:45Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — a deck with `A.advances=[B]` and `B.advanced_by: "<string>"` reports the missing reverse half from `find_half_edges` instead of an empty list. Regression test lands in `tests/`.
  - [x] MECHANICAL: `goc/engine.py` `find_half_edges` (engine.py:1290) wraps `inverse_list = other.frontmatter.get(inverse) or []` with the same `isinstance(..., list)` guard already applied to the outer `v` at engine.py:1297 (treat a non-list inverse as an empty edge set).
  - [x] MECHANICAL: plugin mirrors synced; `uv run goc validate` clean on this repo's deck.
worker: {who: "claude[bot]", where: main}
---

# `find_half_edges` substring-matches a non-list inverse side

## Location

`goc/engine.py:1290-1306` — `find_half_edges`.

## What's broken

The outer walk guards against a non-list `advances` / `advanced_by` value:

```python
for field, inverse in INVERSE_REL.items():
    v = t.frontmatter.get(field) or []
    if not isinstance(v, list):
        continue
    for ref in v:
        other = by_title.get(ref)
        if other is None:
            continue
        inverse_list = other.frontmatter.get(inverse) or []
        if t.title not in inverse_list:
            half_edges.append(HalfEdge(t.title, field, ref, inverse))
```

The INNER `inverse_list` carries no `isinstance(..., list)` guard. When
the neighbour's inverse field is a hand-edited bare string (the YAML
emitter writes block-style lists, but hand edits can land a scalar),
`inverse_list` becomes a `str`. The `t.title not in inverse_list` then
falls back to Python's *substring* `__contains__` — a substring hit
silently affirms a reverse edge that does not structurally exist.

## Empirical evidence

Two cards, one valid edge plus a hand-edited bare-string inverse:

```
deck/acard/README.md  →  advances: [bcard]
deck/bcard/README.md  →  advanced_by: "acard-suffix-that-contains-acard"
```

Ground truth: `bcard.advanced_by` is a string (not a list), so the
symmetric edge for `acard.advances=[bcard]` is missing. Expected:
`repair-edges` lists a half-edge for the `acard → bcard` direction.

Actual:

```
$ uv run goc repair-edges
No half-edges found.
```

The `"acard" in "acard-suffix-that-contains-acard"` substring match
returns true, so the inner check skips. (Even an exact-match bare
string — `advanced_by: "acard"` — silently passes for the same reason:
`"acard" in "acard"` is true, but the value is still not a valid list.)

## Why it matters — reachability

The frontmatter emitter (`engine.py` `dump_frontmatter` writers) always
writes block-style lists; this malformation comes from **hand edits**
of `deck/<title>/README.md`, exactly the consumer path the
`compute-values-iterates-non-list-advances-character-by-character`
closure was filed for. `validate_card` (engine.py:1233-1237) does
catch the bare-string inverse via `must be a list`, so `goc validate`
won't pass — but the user-facing failure mode is `goc repair-edges`
reporting "No half-edges found." while the deck is in fact asymmetric.
That's the wrong signal for the symptom, and it's the same inner-
versus-outer guard gap fixed in the previous sibling commit (5dd921c).

`_cmd_repair_edges` (engine.py:4201) calls `find_half_edges` without
first running `validate_card`, so the user can hit the silent path
without seeing the upstream `must be a list` error.

## Fix

Add the same `isinstance(..., list)` guard to the inner `inverse_list`:

```python
inverse_list = other.frontmatter.get(inverse) or []
if not isinstance(inverse_list, list):
    inverse_list = []
if t.title not in inverse_list:
    half_edges.append(HalfEdge(t.title, field, ref, inverse))
```

This mirrors the existing outer guard, the comment block at
`compute_values` (engine.py:1822-1826: "mirrors `find_half_edges` /
`validate_card`"), and the closed sibling fix. After the fix,
`repair-edges` correctly surfaces the asymmetry, and the user is
prompted to repair (or to run `goc validate` for the upstream cause).

## Sibling sweep

Already swept by the closed sibling `compute-values-iterates-non-list-
advances-character-by-character` (engine.py compute_values, detect_
advance_cycles, _would_create_advance_cycle). This card adds
`find_half_edges`'s inner walk. After this lands, an architectural
meta-fix card would be appropriate only if a 4th instance surfaces.

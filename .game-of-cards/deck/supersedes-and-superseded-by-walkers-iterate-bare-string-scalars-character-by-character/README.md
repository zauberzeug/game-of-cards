---
title: supersedes-and-superseded-by-walkers-iterate-bare-string-scalars-character-by-character
summary: "Three engine walkers (`validate_supersedes_targets`, `detect_supersedes_cycles`, `_would_create_supersedes_cycle`) iterate `supersedes` / `superseded_by` frontmatter values without an `isinstance(x, list)` guard. A hand-edited card with a bare-string `supersedes: <slug>` (instead of a list) makes the loops walk the string character-by-character; any one-character title in the deck silently matches and lets dangling pointers slip past `goc validate`. Same family as the just-closed tags / inverse-half-edge fixes."
status: done
stage: null
contribution: medium
created: "2026-05-29T05:48:30Z"
closed_at: 2026-05-29T05:55:19Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero (defect no longer fires — `validate_supersedes_targets` reports the dangling bare-string target).
  - [x] MECHANICAL: `validate_supersedes_targets` (engine.py:1278), `detect_supersedes_cycles` (engine.py:1385), and `_would_create_supersedes_cycle` (engine.py:1413) each guard their iteration with `if not isinstance(v, list): continue` (or equivalent), matching the pattern already present in `detect_advance_cycles` (engine.py:1326) and `_would_create_advance_cycle` (engine.py:1354).
  - [x] TDD: a regression test in `tests/` exercises the bare-string `supersedes` path and asserts validation flags it (mirroring `test_card_tags.py` / `test_find_half_edges.py` shape from the sibling fixes).
  - [x] MECHANICAL: `uv run goc validate` clean; `pre-commit run --all-files` clean (plugin mirrors auto-sync).
worker: {who: "claude[bot]", where: main}
---

# `supersedes` and `superseded_by` walkers iterate bare-string scalars character-by-character

## Location

`goc/engine.py`:

- `validate_supersedes_targets`, line 1278 — `for ref in t.frontmatter.get("supersedes") or []:`
- `detect_supersedes_cycles`, lines 1385–1386 — `superseded_by = t.frontmatter.get("superseded_by") or []` then `for b in superseded_by:`
- `_would_create_supersedes_cycle`, line 1413 — `for s in card.frontmatter.get("superseded_by") or []:`

## What's broken

All three sites do the same `frontmatter.get(<field>) or []` lookup, then iterate. The `or []` only triggers when the value is falsy (None / missing / empty). A hand-edited card with a bare-string scalar like `supersedes: some-card` parses as the truthy string `"some-card"`, the `or []` is skipped, and the `for` loop walks the string **character by character**.

The sibling code for the `advances` family was hardened against exactly this shape:

```python
# engine.py:1326-1328 — detect_advance_cycles (GUARDED)
advanced_by = t.frontmatter.get("advanced_by") or []
if not isinstance(advanced_by, list):
    continue
for b in advanced_by:
    ...
```

```python
# engine.py:1354-1356 — _would_create_advance_cycle (GUARDED)
advances = card.frontmatter.get("advances") or []
if not isinstance(advances, list):
    continue
for a in advances:
    ...
```

The same guard is missing on the supersession side:

```python
# engine.py:1278 — validate_supersedes_targets (UNGUARDED)
for ref in t.frontmatter.get("supersedes") or []:
    target = by_title.get(ref)
    ...
```

```python
# engine.py:1385-1386 — detect_supersedes_cycles (UNGUARDED)
superseded_by = t.frontmatter.get("superseded_by") or []
for b in superseded_by:
    ...
```

```python
# engine.py:1413 — _would_create_supersedes_cycle (UNGUARDED)
for s in card.frontmatter.get("superseded_by") or []:
    ...
```

## Empirical evidence

`uv run python deck/<title>/reproduce.py` (see `reproduce.py`):

```
validate_supersedes_targets errors: []
```

Two cards in memory:

- `a` with `supersedes: "nonexistent"` (bare string, hand-edited shape)
- `n` with `status: superseded`

Expected: `validate_supersedes_targets` flags `'nonexistent'` as not-found-or-not-superseded (the typed supersession pointer is dangling).

Actual: the loop iterates `"nonexistent"` character-by-character; the character `'n'` matches the title of card `n`, whose status IS `superseded`, so the check silently passes. The dangling reference never reaches the validator's error list.

## Why it matters — reachability

`goc new` / `goc advance` write list-style frontmatter, so a fresh card never carries a bare-string `supersedes:` value. The hand-edit path is the reachability:

- A maintainer hand-edits a card's frontmatter (e.g. fixing a typo, copying from another card's body, or pasting from a chat snippet) and types `supersedes: <slug>` without the `[ ]` brackets.
- A migration script or `goc migrate-list-style` interim state can also leave a list field as a scalar.

When that input flows through `goc validate`, the integrity check the function exists to enforce — "every card in `supersedes` must itself be `status: superseded`" — silently passes. The record-axis routing for a cold reader is broken (the typed forward pointer points at nothing real) and the validator does not surface it. Same shape as the just-merged fixes:

- [tags-property-iterates-bare-string-tags-character-by-character](../tags-property-iterates-bare-string-tags-character-by-character/) (closed 2026-05-29) — fixed `Card.tags` to guard non-list tags.
- [repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string](../repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string/) (closed 2026-05-29) — fixed `find_half_edges` to guard non-list inverse with `isinstance`.

This is the third confirmed instance in the family. Per `Skill(audit-deck)`'s sibling-sweep rule, a fourth instance would warrant a meta-fix card; three sites in the same supersedes family in this same file is still within the per-card threshold.

## Fix

Add the same `isinstance(..., list)` guard already used in `detect_advance_cycles` and `_would_create_advance_cycle` to all three supersession walkers. Concrete shape, mirroring the guarded siblings:

```python
# validate_supersedes_targets (~line 1277)
for t in cards:
    refs = t.frontmatter.get("supersedes") or []
    if not isinstance(refs, list):
        continue
    for ref in refs:
        ...

# detect_supersedes_cycles (~line 1385)
superseded_by = t.frontmatter.get("superseded_by") or []
if not isinstance(superseded_by, list):
    continue
for b in superseded_by:
    ...

# _would_create_supersedes_cycle (~line 1413)
succs = card.frontmatter.get("superseded_by") or []
if not isinstance(succs, list):
    continue
for s in succs:
    ...
```

A separate question (out of scope here, file as a sibling card if pursued): should `goc validate` upstream-reject bare-string scalars on list-typed fields entirely, so the read-time backstops aren't load-bearing? `_BLOCK_LIST_FIELDS` already encodes which fields are list-typed; a single shape-check at parse time would close the family at the source. For now, this card just adds the read-time guards on the three remaining unguarded sites — consistent with the just-merged sibling fixes.

---
title: tags-property-iterates-bare-string-tags-character-by-character
summary: "The `Card.tags` property returns `frontmatter.get('tags') or []` with no isinstance guard. A hand-edited bare-string `tags: bug` then flows into the render path (line 2171, `','.join(t.tags[:4])` → `'b,u,g'`) and the tag-filter (line 1921, `tag in t.tags` substring-matches via Python's string `in`). Same root-cause family as the recently-closed `compute-values-iterates-non-list-advances-character-by-character` and `repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string`."
status: done
stage: null
contribution: medium
created: "2026-05-29T05:34:42Z"
closed_at: 2026-05-29T05:40:08Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (renders the bare-string tag verbatim instead of `b,u,g`, and `goc --tag b` does NOT match a card whose only tag string is `bug`).
  - [x] MECHANICAL: `Card.tags` (or its single consumer site) coerces a non-list value to `[]` (or to `[value]` if the value is a non-empty string) BEFORE returning, mirroring the `isinstance(..., list)` guard added in `bd03d91` for `find_half_edges` and earlier for `compute_values`.
  - [x] TDD: a regression test under `tests/` covers a card whose frontmatter has `tags: bug` (bare string) — both render and filter paths must behave as if the field were `[]` (or as if it were a single-element list, depending on the chosen coercion; record the choice in log.md).
  - [x] MECHANICAL: plugin mirrors synced (`python scripts/sync_plugin_assets.py --check` green).
worker: {who: "claude[bot]", where: main}
---

# `Card.tags` iterates bare-string tags character-by-character

## Location

- `goc/engine.py:507` — the property itself, no isinstance guard.
- `goc/engine.py:1921` — filter site uses Python's `in` against the
  return value (substring match instead of list-membership when value
  is a string).
- `goc/engine.py:2171-2173` — render site slices and joins the return
  value (treats the string as an iterable of characters).

## What's broken

The `Card.tags` property is defined as:

```python
@property
def tags(self) -> list[str]:
    return self.frontmatter.get("tags") or []
```

The `or []` fallback handles `None` / missing, but NOT a non-list
truthy value. Two reachable consumer sites then misbehave when a card's
frontmatter has been hand-edited to `tags: bug` (bare string, valid YAML,
but the wrong shape):

**Filter (line 1921):**

```python
if tags:
    out = [t for t in out if all(tag in t.tags for tag in tags)]
```

`tag in t.tags` falls through to Python's string `in` operator (substring
match) instead of list-membership. So `goc --tag b` matches a card with
`tags: bug`, and `goc --tag bug` matches a card with `tags: bug-other`.

**Render (lines 2171-2173):**

```python
tags = ",".join(t.tags[:4])
if len(t.tags) > 4:
    tags += "+"
```

Slicing the string gives `"bug"[:4]` → `"bug"`, then `",".join("bug")`
iterates characters → `"b,u,g"`. The TAGS column in `goc` / `goc --board`
shows garbage.

`goc validate` does catch the shape (`engine.py:1185-1187`,
`tags: must be a list`), but neither `goc` (default queue) nor `goc
--tag X` nor `goc --board` runs the validator first — they hit the
unsafe property path immediately.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/tags-property-iterates-bare-string-tags-character-by-character/reproduce.py
render of card with tags='bug':      'b,u,g'
filter '--tag b' matches card with tags='bug': True   (BUG: should be False)
filter '--tag bug-other' matches card with tags='bug': False  (correct)
```

## Why it matters

Reachability: a human hand-edits frontmatter and writes `tags: bug`
instead of `tags: [bug]` (valid YAML, accidentally scalar). The emitter
in this repo writes inline flow style for `tags:` so the round-trip is
clean from the engine's side — but the *input* path is not guarded.
Any agent or human editing a card by hand can trigger this.

Same root-cause family as two closed siblings, both fixed by adding
`isinstance(..., list)` guards at the iteration site:

- [compute-values-iterates-non-list-advances-character-by-character](../compute-values-iterates-non-list-advances-character-by-character/)
  (done) — `compute_values` walking `advances` as a string.
- [repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string](../repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string/)
  (done, commit `bd03d91`) — `find_half_edges` substring-matching the
  inverse list pulled from a neighbour.

The `Card.tags` property is the same hazard, in a hotter path
(every queue render reads it; every `--tag X` filter reads it).

## Fix

The minimal fix mirrors the sibling pattern:

```python
@property
def tags(self) -> list[str]:
    v = self.frontmatter.get("tags")
    return v if isinstance(v, list) else []
```

The siblings chose `[]` (treat malformed as empty); this is safest
because it does not silently turn a typo into a single-element list
that misleads filters downstream. Record the choice in `log.md`. The
validator will still flag the bad shape on the next `goc validate`
run; the fix simply prevents silent misbehavior in render/filter
before validation runs.

---
title: advances-and-advanced-by-cli-filters-substring-match-bare-string-scalars
summary: "`filter_cards` (engine.py:1949-1952) uses Python's `in` operator on `t.frontmatter.get('advances')` / `t.frontmatter.get('advanced_by')` without coercing to list, so a bare-string scalar value silently switches `in` from list-membership to substring-matching. Same sibling shape as the recently-patched supersedes/dependency_blockers/compute_values/tags walkers, this time reaching the public `goc --advances <title>` / `goc --advanced-by <title>` CLI surface. A query token that is a substring of any card's scalar edge value produces a false positive."
status: done
stage: null
contribution: medium
created: "2026-05-29T06:15:22Z"
closed_at: 2026-05-29T06:20:45Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — `filter_cards` returns `[]` for the `'foo'` query against a card with bare-string `advances: 'foo-card-extended'`, instead of falsely matching by substring.
  - [x] TDD: a regression test in `tests/` asserts that `--advances <title>` / `--advanced-by <title>` filters treat a non-list edge value as no membership at all, mirroring the `isinstance(..., list)` guard the recent walker fixes added in `dependency_blockers`, `compute_values`, the supersession cycle walkers, and the `tags` property.
  - [x] MECHANICAL: the two unguarded `in` comparisons at `goc/engine.py:1950` and `goc/engine.py:1952` coerce the frontmatter value to a list before the membership test (or call a shared list-coercion helper consistent with the existing walker fixes).
  - [x] PROCESS: full regression suite green (`uv run python -m unittest discover -s tests`); plugin mirrors synced if `engine.py` changed (pre-commit `sync-plugin-assets`).
worker: {who: "claude[bot]", where: main}
---

# `--advances` and `--advanced-by` CLI filters substring-match bare-string edge scalars

## Location

`goc/engine.py:1949-1952` — inside `filter_cards`:

```python
if advances:
    out = [t for t in out if advances in (t.frontmatter.get("advances") or [])]
if advanced_by:
    out = [t for t in out if advanced_by in (t.frontmatter.get("advanced_by") or [])]
```

`t.frontmatter.get("advances")` returns whatever the parser produced
for that field. When the value is a list (the canonical shape), `in`
checks membership and behaves correctly. When the value is a bare
string scalar (a still-valid legacy YAML shape — the same shape that
the recent walker-fix family discovered in `dependency_blockers`,
`compute_values`, the supersession cycle walkers, and the `tags`
property), `in` silently switches from list-membership to Python
substring-matching on the string.

## What's broken

The two filters fail in two ways at once on a card whose edge field
is a bare string:

1. **False positives.** A query that is a substring of the scalar's
   text matches the card even though the query is not a real card
   title. `--advances foo` matches a card whose `advances:
   foo-card-extended`.
2. **Shape-dependent inconsistency.** Two cards with identical edge
   semantics — one written `advances: "foo-card"` and the other
   `advances: ["foo-card"]` — answer `--advances foo-card-prefix`
   queries differently. The scalar shape says yes (substring); the
   list shape says no (membership).

The fix shape the rest of the walker family already settled on is
to coerce the value to a list before the membership test:

```python
adv = t.frontmatter.get("advances")
adv = adv if isinstance(adv, list) else []
out = [t for t in out if advances in adv]
```

or call a shared helper that the recent walker fixes can reuse.

## Empirical evidence

`uv run python .game-of-cards/deck/advances-and-advanced-by-cli-filters-substring-match-bare-string-scalars/reproduce.py`
output on the bug:

```
substring foo matched: ['scalar-card']
full title match: ['scalar-card', 'list-card']
DEFECT: --advances 'foo' returned ['scalar-card'] (expected []).
```

The first line is the smoking gun — the query `'foo'` (which is not
a card title) matches the card whose `advances` is the unrelated
scalar `'foo-card-extended'`. Once the `in` test is guarded by
`isinstance(..., list)`, that line becomes `substring foo matched:
[]` and the script exits zero.

## Why it matters

`Card.frontmatter` is the raw parser output. The parser does not
canonicalize edge fields to a list — that is what each read-time
consumer is expected to do, which is exactly what the recent
walker-fix family established. The same parser/emitter regime that
produces a bare-string `advanced_by` on `dependency_blockers'`
inputs (`engine.py:1693`) and a bare-string `supersedes` on the
cycle walkers (`engine.py:1336, 1395`) also produces a bare-string
`advances` reaching `filter_cards`. Reachability is therefore
identical to the already-confirmed sibling cases — a hand-edited
card or a partially-migrated card with `advances: foo-card-extended`
flows through the public CLI surface (`uv run goc --advances foo`
or `uv run goc --advanced-by foo`) with the same trigger shape.

The public CLI surface raises the visibility: `goc --advances
<title>` is the documented query an autonomous agent or human uses
to inspect a card's dependents during planning, edge-repair, and
release coordination. A false-positive match steers a reader to a
card that does not actually advance the queried target.

## Fix

Apply the `isinstance(..., list)` guard at the two unguarded
sites, matching the convention already in place for the other
walker fixes. The two-line patch is the entire change; no edge
semantics shift.

Optional follow-up (out of scope for this card): factor a single
`_edge_list(card, field) -> list[str]` helper and route every
read-time edge consumer through it, so a future bare-string
parser regression cannot reach `engine.py` consumers without
hitting the canonical guard. File as a separate refactor card
if there is appetite.

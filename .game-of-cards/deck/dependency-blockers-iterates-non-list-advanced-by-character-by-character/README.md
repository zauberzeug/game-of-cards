---
title: dependency-blockers-iterates-non-list-advanced-by-character-by-character
summary: "`dependency_blockers` (engine.py:1693) iterates `frontmatter['advanced_by']` without an `isinstance(..., list)` guard, so a hand-edited bare-string scalar is walked character-by-character — each character becomes a phantom blocker. Reachable on every `goc -v`, `goc --json`, and `goc --board` invocation (the verbose `awaiting:` line, the JSON `awaiting`/`dependency_awaiting` fields, and the board ⏳ glyph). Same root-cause shape as the recently-fixed `compute_values` / `supersedes` / `tags` walkers; three sibling read-time consumers carry the same unguarded pattern."
status: active
stage: null
contribution: medium
created: "2026-05-29T06:03:10Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a card with a bare-string `advanced_by: "abc"` returns `[]` from `dependency_blockers` (not `['a','b','c']`), and `dependency_blocked` returns False.
  - [ ] TDD: a regression test in tests/ asserts the read-time consumers treat a non-list `advanced_by` / `advances` as an empty edge set, mirroring the guard already present in `compute_values` (engine.py:1864) and the supersession cycle walkers (engine.py:1336, 1395).
  - [ ] MECHANICAL: the four unguarded sites add an `isinstance(..., list)` guard before iterating: `dependency_blockers` (engine.py:1693), `live_direct` inside `_live_edge_count` (engine.py:2090), `_run_derived_check`'s `advanced-by-closed` branch (engine.py:3719), and `validate_blocker_coherence`'s `unblocks` builder (engine.py:1594). The other two sibling sites — the over-broad-epic detector (engine.py:1524) and `validate_blocker_coherence`'s blocker enumerator (engine.py:1601) — are only reached for `status: blocked` cards (a status on its way out) but receive the same guard for consistency.
  - [ ] PROCESS: full regression suite green (`uv run python -m unittest discover -s tests`); plugin mirrors synced if engine.py changed (pre-commit `sync-plugin-assets`).
worker: {who: "claude[bot]", where: main}
---

# `dependency_blockers` iterates a non-list `advanced_by` field character-by-character

## Location

`goc/engine.py:1693` — inside `dependency_blockers`:

```python
def dependency_blockers(card: Card, by_title: dict[str, Card]) -> list[str]:
    blockers: list[str] = []
    for prereq in card.frontmatter.get("advanced_by") or []:
        upstream = by_title.get(prereq)
        if upstream is None or upstream.status not in TERMINAL_STATUSES:
            blockers.append(prereq)
    return blockers
```

## What's broken

`advanced_by` is contractually a **list** of card titles. The validator
knows this (`engine.py:1235`):

```python
if v and not isinstance(v, list):
    errors.append(f"{t.title}: {field}: must be a list")
```

The sibling `compute_values` (engine.py:1864) and the supersession
cycle walkers (engine.py:1336, 1395) all guard against the non-list
shape, after the four closed cards in this family — `compute-values-…`,
`tags-property-…`, `supersedes-and-superseded-by-walkers-…`, and
`repair-edges-misses-half-edge-…`.

But `dependency_blockers` — which is the **read-time scheduler-axis
dependency-readiness predicate**, run on every `goc -v` / `goc --json`
/ `goc --board` invocation (a path that is *not* gated by
`goc validate`) — has no such guard. When a card's frontmatter is
hand-edited to the YAML scalar form `advanced_by: abc` (a bare string
instead of a list), Python iterates the string character by character.
Each character is treated as a possible upstream title:

- `by_title.get('a')`, `by_title.get('b')`, `by_title.get('c')` —
  return `None` for nonexistent titles;
- each `None` upstream is treated as a **non-terminal blocker** (the
  function's conservative dangling-reference policy) and appended;
- the function returns `['a', 'b', 'c']` and `dependency_blocked`
  returns `True`.

Three sibling read-time consumers carry the same unguarded shape:

- `live_direct` (engine.py:2090) inside `_live_edge_count` — the
  value-sort tiebreak that counts live downstream `advances`. Bare
  string ⇒ phantom characters become spurious live edges; the
  tiebreak inflates.
- `_run_derived_check` `"advanced-by-closed"` branch
  (engine.py:3719) — the closure-gate DoD derived check. Bare string
  ⇒ `if not advanced_by:` is False (non-empty string is truthy), then
  the character-by-character walk silently returns "all closed" if no
  single-character title happens to match. The closure gate fails to
  flag the malformed field.
- `validate_blocker_coherence` `unblocks` builder (engine.py:1594) —
  reverse adjacency for the downstream-stuck detector. Bare string ⇒
  if any single-character title exists in the deck, false unblock
  edges are added to the dict.

Two more sibling sites are reached only inside `status: blocked`
branches (engine.py:1524, 1601). With `blocked` being removed from
the status enum (epic `remove-blocked-from-status-enum-and-migrate-existing-cards`),
these are increasingly dead but still executable; they get the same
guard for consistency.

## Empirical evidence

`uv run python .game-of-cards/deck/dependency-blockers-iterates-non-list-advanced-by-character-by-character/reproduce.py`:

```
dependency_blockers returned: ['a', 'b', 'c']
count: 3
dependency_blocked returned: True
```

Expected (after fix): `[]`, count `0`, `False`.

## Why it matters

The defect surfaces wherever a card's `advanced_by` is hand-authored
as a bare-string scalar — the same authoring path that produced the
already-fixed `supersedes` / `tags` / `advances` instances. Frontmatter
emitter writes list fields in block style today, so the typical write
path is safe; the reachability path is **hand-editing** (an agent or
human dropping `advanced_by: foo` in a one-shot, or pre-emitter
legacy cards in older repos), which `goc validate` catches only when
it's run — but `dependency_blockers` is consulted on every read path
that doesn't go through `validate`:

- `goc -v` verbose listing (engine.py:2232-2234) — emits a bogus
  `awaiting: a, b, c` line.
- `goc --json` machine-readable output (engine.py:2310-2311) — leaks
  the phantom list to consumers via the `awaiting` /
  `dependency_awaiting` fields.
- `goc --board` (engine.py:2362) — paints the card with the ⏳
  hourglass glyph as derived-blocked.

The closure-gate path (`_run_derived_check`, engine.py:3719) is more
serious: it determines whether `goc done` can close a card with an
`advanced-by-closed` derived-check DoD item. A bare-string
`advanced_by` silently passes that gate when it should fail.

## Fix

Add an `isinstance(..., list)` guard before iterating, mirroring the
existing guard in `compute_values` (engine.py:1864):

```python
def dependency_blockers(card: Card, by_title: dict[str, Card]) -> list[str]:
    blockers: list[str] = []
    prereqs = card.frontmatter.get("advanced_by") or []
    if not isinstance(prereqs, list):
        return []
    for prereq in prereqs:
        upstream = by_title.get(prereq)
        if upstream is None or upstream.status not in TERMINAL_STATUSES:
            blockers.append(prereq)
    return blockers
```

Apply the same guard to the three other unguarded read-time sites
(engine.py:2090, 3719, 1594), and to the two `status: blocked`-only
sites (engine.py:1524, 1601) for consistency. The validator already
emits the canonical error message at the validate-time backstop
(engine.py:1235); the read-time guards just need to be defensive.

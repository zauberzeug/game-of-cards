---
title: sort-tiebreak-double-counts-duplicate-advances-edges
status: done
stage: null
contribution: medium
created: "2026-06-24T08:12:26Z"
closed_at: "2026-06-24T08:16:30Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "`sort_default`'s near-term-flow tiebreak (`live_direct`, `goc/engine.py:2637-2649`) counts raw `advances` list elements rather than distinct workable targets, so a card padding its `advances` list with a repeated slug inflates its tiebreak score and can out-rank a card that genuinely unblocks more distinct downstream work."
definition_of_done: |
  - [x] EMPIRICAL: `reproduce.py` builds a clean-validating deck where one
        card has a duplicated `advances` edge and another has two distinct
        edges, shows the duplicate-edge card ties/beats the distinct-edge
        card on the near-term-flow tiebreak (current bug), then passes once
        deduped.
  - [x] MECHANICAL: `live_direct` in `sort_default` counts *distinct*
        workable downstream targets, not raw list elements.
  - [x] TDD: a regression test in `tests/` asserts the tiebreak deduplicates
        repeated `advances` entries.
  - [x] PROCESS: `uv run goc validate` passes.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` passes.
worker: {who: "claude[bot]", where: main}
---

# Sort tiebreak double-counts duplicate `advances` edges as distinct downstream flow

## Problem

`sort_default`'s near-term-flow tiebreak counts raw list elements of
`advances` rather than distinct workable targets. A card padding its
`advances` list with a repeated slug inflates its tiebreak score and
can out-rank — or tie-then-win-by-age against — a card that genuinely
unblocks more distinct downstream work.

The offending helper at `goc/engine.py:2637-2649`:

```python
def live_direct(t: Card) -> int:
    n = 0
    advances = t.frontmatter.get("advances") or []
    if not isinstance(advances, list):
        return 0
    for dest in advances:
        dc = by_title.get(dest)
        if dc is None:
            continue
        if not card_is_workable_for_scheduler(dc):
            continue
        n += 1
    return n
```

`n` increments once per list element. So `advances: [B, B]` yields
`live_direct == 2`, identical to `advances: [B, C]` which unblocks two
genuinely distinct cards. The sort key is
`(-v, -live_direct(t), t.created)` (engine.py:2653).

## Contradiction with the documented contract

The `sort_default` docstring (engine.py:2606-2616) states the tiebreak
counts "more *live* direct downstream cards = unblock more flow now"
and "Counts only `advances` targets the value walk would traverse."
Both phrasings describe distinct downstream *cards*, not list slots.
The code drifted from its own stated contract.

## Reachability (clean-validating input)

`validate_card`'s relationship-field loop (engine.py:1573-1582) checks
only self-reference and unknown-title; it never rejects a duplicate
entry, and `find_half_edges` ignores duplicates too. So a deck with
`advances: [B, B]` passes `goc validate` cleanly. Reachability paths:

- Hand-authored frontmatter — AGENTS.md explicitly allows hand-editing
  the block-style `advances` list, and nothing dedupes it.
- The companion open card
  `goc-advance-claims-success-when-adding-an-already-existing-edge`
  documents that `goc advance` does not hard-fail on an existing edge,
  so the verb path can also leave duplicates behind.

Because the value score itself takes a `max` over descendants in
`compute_values`, the duplicated edge does NOT corrupt the primary
value axis — only the tiebreak axis is wrong, bounding the blast
radius to ordering ties.

## Fix

Deduplicate before counting — count distinct workable target titles
rather than incrementing per list element. The value/edge-graph walk
already drops dangling edges identically, so only the per-element
double-count needs removing.

---
title: compute-values-cycle-fallback-is-order-dependent
summary: "UNVERIFIED. `compute_values`' cycle guard returns `(own, [\"cycle\"])` for a re-entered node WITHOUT caching it, so the first-traversed cycle member absorbs the chained value while the other gets bare rank — making priority order-dependent on the `cards`/`advances` list order. But the docstring says cycles should fall back to per-card rank, AND `detect_advance_cycles` is a validate-gating ERROR (plus `goc advance` refuses cycle-creating edges), so a cycle cannot exist in any deck that passes `goc validate`. Likely unreachable defensive code with a docstring that overclaims; parked pending a reachability decision."
status: open
stage: null
contribution: low
created: "2026-05-26T20:20:14Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, unverified, api-contract]
definition_of_done: |
  - [ ] EMPIRICAL: decide reachability — confirm whether a cycle can ever reach `compute_values` in a deck that passes `goc validate`. Record the verdict in log.md either way.
  - [ ] If reachable: TDD: reproduce.py exits zero — cycle members get order-independent values (true per-card-rank fallback, matching the docstring).
  - [ ] If unreachable: MECHANICAL: correct the docstring (lines 1564-1565) to stop claiming a per-card-rank fallback the code doesn't actually deliver, and disprove/close.
---

# `compute_values` cycle fallback is order-dependent

## Location

`goc/engine.py:1574-1606` — the `value_for` closure inside
`compute_values`. The cycle guard is at line 1581-1582; the cache write
is at line 1605.

## What the hunter claimed (unverified)

The docstring (lines 1564-1565) states:

> Cycles fall back to per-card rank (defense; validator should reject
> cycles via `detect_advance_cycles` but cheap to handle here too).

But the implementation does not deliver an order-independent per-card-rank
fallback. When `value_for` re-enters an in-progress node it returns
`(own, ["cycle"])` **without writing to `cache`** (line 1581-1582,
no cache assignment). The *caller's* result — which folded that cycle
return into its `best` — IS cached (line 1605). So whichever cycle member
is traversed first absorbs the chained value; the other member, traversed
later, is computed from the now-cached partial and gets a different value.
The result depends on the order of the `cards` list and of each card's
`advances` entries.

Hunter's predicted reproduce (NOT yet run):
- Deck: `A advances:[B]`, `B advances:[A]`, both `contribution: high`;
  `X advances:[A]`, `contribution: low`.
- `cards=[A,B,X]` -> `A=19.71, B=15.3`; `cards=[B,A,X]` -> `A=15.3, B=19.71`.
- Expected per docstring: A and B both fall back to bare rank 9.0
  regardless of order.

## Why it is parked unverified, not filed as a live defect

A cycle in the `advances` graph **cannot exist in a deck that passes
`goc validate`**:

- `detect_advance_cycles` results are appended to `errors` and gate the
  exit code (`goc/engine.py:2369-2371`) — a cycle is a hard validation
  ERROR, not a warning.
- `goc advance` refuses any edge that `_would_create_advance_cycle`
  (`goc/engine.py:3728-3729`), so the CLI never writes a cycle.

So the order-dependent fallback is pure defensive code that only executes
on a deck already failing validation. The user-facing priority math is
not corrupted for any valid deck. The docstring's "falls back to per-card
rank" is the real (minor) inaccuracy.

## Falsification recipe

1. Build the A/B/X deck above in a temp dir, call `compute_values` twice
   with the `cards` list in two different orders, and compare A's and B's
   values. If they differ, the order-dependence is confirmed.
2. Separately, confirm reachability: try to create the cycle via
   `goc advance` (expect refusal) and run `goc validate` on a
   hand-authored cyclic deck (expect a gating ERROR). If both block the
   cycle, the defect is unreachable in practice -> downgrade to a
   docstring correction and disprove.

Surfaced by a general-purpose audit hunter on 2026-05-26.

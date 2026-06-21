---
title: repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses
summary: "`goc repair-edges` (dry-run) classifies every half-edge as fixable/structural against ONE original snapshot, while `--apply` reloads before each edge so its cycle checks see earlier same-run repairs. When repairing one half-edge creates the advances cycle that makes a second half-edge structural, the dry-run promises N repairs but apply performs fewer and exits 1. A 4th instance of the dry-run-vs-executor drift meta-fix family, now in repair-edges (not install/migrate)."
status: active
stage: null
contribution: medium
created: "2026-06-21T19:36:04Z"
closed_at: null
human_gate: none
advances:
  - dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — the dry-run "would be repaired (N)" set equals the set `--apply` actually repairs, on a deck where one repair creates a cycle for another
  - [ ] TDD: a regression test asserts dry-run/apply parity for repair classification across an interacting-half-edge fixture (two Type-β advances half-edges that form a cycle when both reverse halves are added)
  - [ ] MECHANICAL: the dry-run classification loop in `_cmd_repair_edges` (`engine.py`) simulates earlier same-run repairs the way `--apply` reloads — i.e. the two loops no longer compute fixable/structural from different graph snapshots
  - [ ] PROCESS: forward pointer added to the root meta-fix card `dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting` (this instance recorded under "instances so far")
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` passes
worker: {who: "claude[bot]", where: main}
---

# `goc repair-edges` dry-run overstates the repairs that `--apply` will make

## Location

`goc/engine.py:4931` — `_cmd_repair_edges`. The dry-run classification
loop is `engine.py:4941-4946`; the `--apply` loop is `engine.py:4964-4977`.

## What's broken

The two branches of `_cmd_repair_edges` classify half-edges as
`fixable` vs `structural` using **different graph snapshots**.

The dry-run loop runs every check against the single deck snapshot
loaded once at the top:

```python
cards = load_all_cards()
half_edges = find_half_edges(cards)
...
for edge in half_edges:
    problem = _repair_edge_cycle_problem(edge, cards)   # <- always the ORIGINAL cards
    if problem:
        structural.append((edge, problem))
    else:
        fixable.append(edge)
```

The `--apply` loop deliberately re-loads before each edge so later
cycle checks observe earlier repairs from the same invocation:

```python
for edge in half_edges:
    # Re-load before each mutation so cycle checks see earlier repairs from
    # this invocation.
    current_cards = load_all_cards()
    problem = _repair_edge_cycle_problem(edge, current_cards)   # <- sees prior same-run repairs
    if problem:
        structural.append((edge, problem))
        continue
    _mutate_pair(edge.ref, edge.src, edge.inverse, edge.field, add=True)
    ...
```

Because the dry-run never reflects an earlier repair, it can only ever
be *more permissive* than apply: the dry-run set of fixable edges is a
superset of what apply actually repairs. When repairing one half-edge
adds the `advances` forward edge that closes a cycle for a second
half-edge, the dry-run reports both as "would be repaired" while apply
repairs only the first and prints the second under "Structural problems
requiring human review", exiting 1.

The dry-run banner is documented as a faithful preview — `Dry run — no
changes made. Run 'goc repair-edges --apply' to write fixes.` — but the
preview lists fixes apply will refuse.

## Empirical evidence

`reproduce.py` builds a two-card deck with two interacting advances
half-edges (`card-a.advanced_by=[card-b]` with `card-a.advances`
missing `card-b`, and the symmetric pair on `card-b`), then runs both
passes:

```
=== DRY RUN ===
Half-edges that would be repaired (2):
...
=== APPLY ===
Structural problems requiring human review:
  card-b: advanced_by contains 'card-a' but card-a.advances is missing 'card-b' (half-edge): card-a → card-b would create a cycle in the advances graph
repaired: card-a: advanced_by contains 'card-b' but card-b.advances is missing 'card-a' (half-edge)
Repaired 1 half-edge(s).
apply exit: 1

DIVERGENCE: dry-run promised 2 repairs; apply performed 1.
```

## Why it matters

`repair-edges` is the recovery tool for a deck whose bidirectional edges
have gone asymmetric, and `--dry-run` is exactly the pass a cautious
operator runs first to see what will change. Reachability is concrete:
the offending input is any deck with two half-edges whose reverse-half
repairs together form an `advances` cycle — a state `find_half_edges`
surfaces by design and that `repair-edges` exists to operate on (the
deck need not pass `goc validate`). The operator reads "would be repaired
(2)", runs `--apply`, and gets 1 repair plus a non-zero exit — the
preview lied about both the count and the success.

This is the same root-cause shape as the
[dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting](../dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting/)
meta-fix family: two code paths encode the same decision (here, the
half-edge classification) and drift because nothing forces them to
agree. The three instances catalogued there all live in
`install`/`upgrade`/`migrate` (`_plan_writes` / the migrate preview);
this is the first instance outside that cluster, in `repair-edges`,
which broadens the case that the architectural fix should be general
rather than per-verb.

## Fix

Make the dry-run classification loop simulate earlier same-run repairs
so it computes against the same evolving graph `--apply` sees. Because
the dry-run writes nothing, it cannot re-`load_all_cards()`; instead it
must mutate the in-memory `cards` (append the reverse-half value to the
relevant `advances`/`advanced_by` list of the affected card) after
classifying each edge as fixable, mirroring `_mutate_pair`'s effect on
the graph. The cleanest form routes both loops through one incremental
classifier so they cannot drift again — which is the deliverable the
root meta-fix card's parity-harness DoD is meant to enforce. Do NOT
apply the fix here; this card records the instance and its evidence.

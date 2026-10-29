---
title: advances-graph-readers-each-trust-one-field-and-disagree-on-half-edged-decks
summary: "Each consumer of the advances relation reads one half of every two-sided edge: the priority walk, the sort, both cycle checks and the --advances filter read advances, while readiness, the advanced-by-closed closure check, the --advanced-by filter and the cascade warning read advanced_by. Where a hand edit left a half-edge, the two groups see different graphs until goc repair-edges runs, and repair-edges itself classifies a cycle differently depending on which half recorded it. Decide whether every consumer should read one relation (an edge counts when either half records it) or whether the goc validate half-edge error is bound enough."
status: open
stage: null
contribution: low
created: "2026-10-29T05:13:38Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - advance-cycle-detectors-walk-different-edge-fields
tags: [meta-fix, api-contract]
definition_of_done: |
  - [ ] PROCESS: pick option A, B or C from `## Decision required` and record the choice and its rationale in log.md.
  - [ ] TDD: under A or B, reproduce.py exits zero — the six consumers it probes give one answer on each half-edge fixture; under C, log.md records why the split is accepted and the card closes without a code change.
  - [ ] MECHANICAL: under A or B, every consumer listed under Location reads the edge through the chosen relation, and a regression test fails when a graph consumer reads `advances` or `advanced_by` directly.
  - [ ] TDD: under A, `tests/test_repair_edges.py` is re-pinned for the new classification of an `advanced_by`-recorded cycle, and `tests/test_advance_cycle_walkers_agree.py` asserts that both cycle walkers see that cycle.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
---

# Advances-graph readers each trust one field and disagree on half-edged decks

## Location

Every reader of the advances relation picks one of its two fields:

| Consumer | Reads | Site |
|---|---|---|
| `compute_values`, the priority walk | `advances` | `goc/engine.py:3261` |
| `live_direct` in `sort_default` | `advances` | `goc/engine.py:3586` |
| `detect_advance_cycles`, the `goc validate` cycle gate | `advances` | `goc/engine.py:2324` |
| `_would_create_advance_cycle`, the guard of `advance`, `new` and `repair-edges` | `advances` | `goc/engine.py:2354` |
| `validate_epic_edge_direction` (`BACKWARDS_EPIC_EDGE`) | `advances` | `goc/engine.py:2516` |
| `filter_cards` for `--advances` | `advances` | `goc/engine.py:3361` |
| `dependency_blockers`, readiness and the `awaiting:` line | `advanced_by` | `goc/engine.py:2741` |
| the `advanced-by-closed` attest check | `advanced_by` | `goc/engine.py:6218` |
| `filter_cards` for `--advanced-by` | `advanced_by` | `goc/engine.py:3368` |
| `validate_blocker_coherence` (`STALE_BLOCKED`, `ORPHAN_BLOCKED`, `CASCADE_CHAIN_ROOT`) | `advanced_by` | `goc/engine.py:2588`, `:2598` |

Only `find_half_edges` (`goc/engine.py:2277`) and the edge-exists checks
in `goc advance` / `goc unadvance` read both halves.

## What's broken

The two fields hold the same edges only on a deck without half-edges. Each
consumer reads the half that matches the direction it walks: forward
consumers read `advances`, backward ones `advanced_by`. So wherever one
half is missing, the consumers split into two groups that see different
graphs. Nothing ties them to one definition of an edge.

`CASCADE_CHAIN_ROOT` shows the drift in its own docstring, which describes
the walk in terms of the other field:

> CASCADE_CHAIN_ROOT: a `human_gate != "none"` card whose `advances`
> transitively reach at least CASCADE_ROOT_THRESHOLD blocked cards.

while the walk builds its adjacency from `advanced_by`:

```python
for c in cards:
    prereqs = c.frontmatter.get("advanced_by") or []
    ...
    for prereq in prereqs:
        if prereq in unblocks:
            unblocks[prereq].append(c.title)
```

## Empirical evidence

`reproduce.py` builds two open cards joined by one edge `up → down`, and
records it in `advances` only, in `advanced_by` only, or in both (the
control). It then asks six consumers whether they see the edge:

```
advances only:
  sees the edge:   value walk, cycle guard, --advances
  misses the edge: readiness, closure check, --advanced-by
advanced_by only:
  sees the edge:   readiness, closure check, --advanced-by
  misses the edge: value walk, cycle guard, --advances
both halves:
  sees the edge:   value walk, cycle guard, --advances, readiness, closure check, --advanced-by
  misses the edge: -

DEFECT: consumers disagree about one edge on: advances only, advanced_by only
```

Each half-edge splits the consumers three to three, and which three see the
edge flips with the half. The control shows that every probe sees a full
edge.

## Why it matters

The split only appears on a half-edged deck, and `goc validate` rejects
those (`validate_bidirectional_edges`), so the bound is real: no deck that
passes validation is affected. But the consumers do not only run on valid
decks. `goc`, `goc --ready`, `goc attest` and `goc repair-edges` run on
whatever the deck holds. Until the deck is repaired, the queue ranks
`up` for unblocking `down` while `down` shows no `awaiting: up`, and the
`advanced-by-closed` check lets `down` close while `up` is still open. The
other half-edge flips every one of these.

`goc repair-edges` is where this matters most, because it only ever runs
on half-edged decks. Its cycle guard reads `advances`, so a cycle recorded
in `advances` has every edge refused as structural, while the same cycle
recorded in `advanced_by` gets every edge repaired except one.

Half-edges come from hand edits and from verb bugs that start from one
(see
[goc-unadvance-with-self-target-leaves-card-in-half-edge-state](../goc-unadvance-with-self-target-leaves-card-in-half-edge-state/)).
`goc new --advances/--advanced-by` and `goc advance` write both halves
together.

The instance that surfaced this,
[advance-cycle-detectors-walk-different-edge-fields](../advance-cycle-detectors-walk-different-edge-fields/),
aligned the one pair that must agree: the `goc validate` cycle gate now
walks `advances`, like the guard. The cost is that a cycle recorded only in
`advanced_by` is read by neither cycle check. That card left reading both
halves to this decision, because doing so changes `repair-edges` behavior.

Related but distinct:
[bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/)
is about the *shape* of a list field, not which half a consumer reads. Its
Option B, a single accessor for list fields, is where a relation accessor
would live if A below is chosen, so the two could land together.

## Decision required

**Option A: one relation, built from both halves.** A single helper builds
the advance edge set, in which `up → down` counts when `up.advances` lists
`down` or `down.advanced_by` lists `up`. Every consumer under Location
derives its direction from that set. This is the edge set `goc
repair-edges` already assumes, since it completes a half-edge rather than
dropping it.

- *Pros:* every view agrees on every deck, and the cycle checks see a cycle
  whichever half records it.
- *Cons:* it touches about ten consumers. Readiness and the closure check
  start honoring half-edges recorded only on the parent. And
  `repair-edges` refuses every edge of an `advanced_by`-recorded cycle
  instead of repairing all but one, which re-pins
  `test_repair_edges_dry_run_matches_apply_on_interacting_half_edges` from
  1 fixable edge to 0.

**Option B: one canonical half.** Consumers read only `advances`, and
backward views invert it. `advanced_by` stays on disk for people reading
the file, but the engine ignores it outside `find_half_edges`.

- *Pros:* one field, one source of truth, and the smallest model.
- *Cons:* a half-edge recorded only in `advanced_by` becomes invisible to
  every consumer. Readiness, which today reads the child's own frontmatter,
  has to scan the whole deck.

**Option C: status quo.** Each consumer reads the half that matches its
direction. `goc validate` fails any half-edged deck and `goc repair-edges`
completes it, so the split lasts only until someone repairs the deck.

- *Pros:* no change.
- *Cons:* the views and `repair-edges` keep running on exactly the decks
  where they disagree.

**Recommendation:** A, ideally landed with the bare-string accessor (that
card's Option B). It is the only option under which every view agrees
without losing an edge one half records. C is defensible while half-edges
stay as rare as they are today.

Decide before claiming this card.

---
title: aggregation-epics-head-block-the-autonomous-pull-queue
summary: "An aggregation epic has no direct work of its own — it closes only when its children close (a closure gate on open `advanced_by`). But its GRPW value composes above its children, so it is the highest-contribution `--ready` card. The autonomous picker selects it every tick, cannot close it, and head-blocks — the exact failure the `remove-blocked-…` decomposition note described for the monolith, now relocated to the parent epic. Decide how the picker should treat pure-aggregator cards."
status: open
stage: null
contribution: medium
created: "2026-05-26T23:33:54Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: pick a mechanism from "## Decision required" (or a fifth) and record the choice + rationale here and in log.md.
  - [ ] MECHANICAL: implement the chosen mechanism in `goc/engine.py`; the pull/next picker no longer offers a pure-aggregator epic that cannot be closed autonomously (its only open `advanced_by` prereq is itself unworkable autonomously — `human_gate: session` or otherwise gated).
  - [ ] TDD: reproduce recipe (below) flips — `goc --ready` on a deck whose only ready cards are aggregation epics gated on a session child no longer offers an unclosable card to the autonomous picker; a regression test encodes this.
  - [ ] MECHANICAL: docs updated — whichever of card-schema / pull-card / next-card / deck / AGENTS describes the ready-to-pull predicate or "Coordinating cards — aggregation epic" reflects the new picker behaviour. Plugin mirrors synced; `uv run goc validate` clean.
---

# Aggregation epics head-block the autonomous pull queue

## What's broken

An **aggregation epic** (per `Skill(card-schema)` "Coordinating cards —
aggregation epic vs governing cluster") has no implementation work of
its own: its DoD is entirely "child X closed" items, and it closes when
its children close. Its closure is therefore gated on its open
`advanced_by` children.

But the GRPW value sort composes a card's value *up* the `advances`
chain (`compute_values`, `engine.py:1670`):
`value(c) = rank(c) + γ·max(value(d) for d in advances(c))`. An epic's
`advances` edge points at its parent, so the epic's value is its own
rank PLUS a discounted share of the chain above it — placing it *above*
its own children in the ranking. The autonomous picker (`card_is_ready`,
`engine.py:1599`) then offers it, because the ready predicate is only:

```python
if card.status != "open":      return False
if card.human_gate != "none":  return False
if waiting_impedes(card):      return False
return True
```

Nothing in that predicate accounts for "this card has no actionable work
and cannot be closed until a child that I am not allowed to pull closes."
So `pull-card` pulls the epic, reads a DoD it cannot satisfy, and exits
without closing. The harness re-triggers fresh, the picker selects the
same epic again — **head-block**.

This is observable on this repo's own deck *right now*. `goc --ready`
offers exactly two cards, both aggregation epics:

```
remove-blocked-from-status-enum-and-migrate-existing-cards      open  medium  5.1  none  ... 0/4
blocked-status-conflates-dependency-external-wait-and-deferral  open  medium  3.0  none  ... 0/5
```

Their only remaining open child is
[`remove-blocked-from-the-status-enum-and-validator`](../remove-blocked-from-the-status-enum-and-validator/)
— `human_gate: session`, deliberately release-coordinated. An
autonomous pull loop instructed to take only `human_gate: none` cards
cannot make progress on either epic, yet they are the *only* things the
picker offers.

## Why it matters — this is the monolith head-block, relocated

The mid epic's own decomposition note
([`remove-blocked-from-status-enum-and-migrate-existing-cards`](../remove-blocked-from-status-enum-and-migrate-existing-cards/),
"Decomposed (2026-05-26)") describes the identical failure for the
pre-split monolith:

> the picker selected it (highest value), spent ~13 min, and exited
> non-zero without closing … it failed every run and head-blocked the
> queue.

Decomposing into children drained the *safe* work autonomously — but the
parent aggregation epic still sits at the top of `--ready`, still
unclosable, still head-blocking. The decomposition moved the symptom up
one level instead of removing it.

## The contract tension

The just-closed
[`make-advances-gate-closure-not-the-pull-queue`](../make-advances-gate-closure-not-the-pull-queue/)
deliberately decided that a non-terminal `advanced_by` prereq must
**NOT** hide a card from the queue — `advances` is "should precede +
gates closure + soft priority", a hard start-gate is the `waiting_on`
overlay. That decision is correct for **loose-contributor** cards: a
card whose upstream merely *contributes* can still be worked (started,
implemented, everything-but-the-final-close).

A **pure aggregator** is categorically different: it has *no* work to
start. The picker offering a loose-contributor is useful; offering a
pure aggregator is always a wasted pull. The fix must not regress the
`make-advances-gate-…` decision for loose-contributors — it must
distinguish "has actionable work, closure-gated" from "no actionable
work at all."

## Reproduce recipe

1. On a deck whose only `human_gate: none` open cards are aggregation
   epics whose sole open child is `human_gate: session` (this repo's
   deck as of 2026-05-26 satisfies this), run `uv run goc --ready`.
2. Observe both ready cards are aggregation epics with `0/N` DoD whose
   unchecked items all reference child closure.
3. `Skill(next-card)` / `pull-card` selects the highest-value one
   (`5.1`). Its DoD cannot be satisfied (open child), so an autonomous
   pull cannot close it → repeated selection of an unclosable card.

A regression test should assert the picker does **not** return such a
card once the chosen mechanism lands, while still returning a
loose-contributor card with an open (workable) `advanced_by`.

## Decision required

How should the picker treat a pure-aggregator card whose closure is
gated on a child that cannot be pulled autonomously? Options:

- **A — Detect & skip pure aggregators in the picker.** Treat a card
  whose every unchecked DoD item references child closure (or: a card
  with non-terminal `advanced_by` and no DoD item that isn't a child
  reference) as non-pullable. Narrow, but the "pure aggregator"
  detection is heuristic and may misfire on epics that also carry a
  doc DoD item.
- **B — Picker skips a card whose every open `advanced_by` prereq is
  itself unpullable** (`human_gate != none`, or `waiting_impedes`, or
  recursively unpullable). Self-clearing: when the gated child becomes
  pullable/closes, the epic re-enters. Closest to the derived-readiness
  spirit; does not regress loose-contributors (a workable open prereq
  still leaves the card offered). Risk: re-introduces a dependency walk
  into the ready predicate that `make-advances-gate-…` just removed —
  needs care to stay advisory for the loose case.
- **C — Give aggregation epics a derived/auto gate.** An epic inherits
  the most-restrictive `human_gate` of its open children (e.g. a child
  at `session` lifts the epic to `session`), so the epic leaves the
  autonomous `none` queue until its children are workable. Keeps the
  picker predicate untouched; moves the logic to gate derivation.
- **D — De-prioritise rather than hide.** Sort closure-gated /
  pure-aggregator cards to the *bottom* of the picker so workable cards
  are always preferred, but still offer them if nothing else is ready.
  Does not fully solve the empty-otherwise case (this repo is in exactly
  that state now), so it likely needs pairing with the empty-queue
  audit-deck fallback.

Recommendation leans **B** (self-clearing, literature-aligned with the
derived-readiness model, no heuristic DoD parsing) — but it must be
scoped so it only fires when the prereq is genuinely *unpullable*, not
merely open, or it re-breaks the loose-contributor decision. A human
should pick before implementation, since this re-touches a contract
settled hours earlier.

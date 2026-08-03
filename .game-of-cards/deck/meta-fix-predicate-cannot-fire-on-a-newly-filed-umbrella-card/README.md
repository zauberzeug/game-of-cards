---
title: meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card
summary: "The `meta-fix` row fires on a literal `meta-fix` in the title, `summary:` or body, or on an edge to another `meta-fix`-tagged card — but this repo names its umbrellas by shape (`…-and-keeps-drifting`, `…-keep-spawning-…-fixes`, `…-is-opt-in-per-…`) and wires their families later, so a freshly filed umbrella satisfies neither clause and scores as mistagged. Measured 2026-08-03: 4 of 54 live tagged cards fail the row, two of them filed after the 2026-07-08 widening; replaying the same sweep at the closure commit with the engine's own parser fails 5 of the same 45 open cards that closure certified clean, so the \"zero false positives\" verification did not hold even when it was written. `Skill(refine-deck)`'s documented action on a plainly-failing evaluable row is to strip the tag, so every hygiene pass is aimed at exactly the curated umbrella grouping the tag exists to provide."
status: active
stage: null
contribution: low
created: "2026-08-03T02:48:05Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [documentation, bug]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — every live `meta-fix`-tagged card satisfies the row as written.
  - [ ] PROCESS: pick the unit of repair and record the reasoning in `log.md` — widen this row a second time, give the table a shared satisfier that umbrella-shaped cards meet by construction, or make the sweep non-destructive on a failing row. The third recurrence is the evidence the row is the wrong unit; see `## Fix`.
  - [ ] MECHANICAL: the chosen wording lands in `goc/templates/skills/card-schema/SKILL.md` (source of truth; mirrors regenerate via the sync hook), and `Skill(refine-deck)` § "Tags without firing predicates" plus `reference.md` § "Tag sweeps" stay consistent with it — the `story` card's closure showed fixing the row alone does not hold, because the sweep restates the contract inline.
  - [ ] TDD: a regression test scores the live tagged population against the row and fails when a card carrying a tag cannot satisfy it, so the next drift is caught by CI instead of by the next refine pass.
  - [ ] MECHANICAL: `uv run goc validate` passes and `python scripts/sync_plugin_assets.py --check` is green.
worker: {who: "claude[bot]", where: main}
---

# The `meta-fix` predicate cannot fire on a newly filed umbrella card

## Location

`goc/templates/skills/card-schema/SKILL.md` § "Canonical tags" (mirrored to
`.claude/skills/card-schema/SKILL.md:256`), the `meta-fix` row as widened by
[meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag](../meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag/)
on 2026-07-08:

```
| `meta-fix` | literal `meta-fix` / `family meta-fix` in title, `summary:`, or full body (no cutoff), OR an `advances`/`advanced_by` edge to a `meta-fix`-tagged card |
```

The consumer is `Skill(refine-deck)` § "Tags without firing predicates",
which instructs the operator to "strip only where a row plainly fails", and
its `reference.md` § "Tag sweeps", which classifies rows into judgment rows
(leave alone) and text-matchable rows (act on):

> **Inability to evaluate a row is not evidence the row fails.** Some rows
> turn on a judgment about what the card delivers or touches [...] and have
> no closed-form text predicate at all. There is nothing to grep. Leave
> these unless the card plainly contradicts the row.

`meta-fix` is not one of those. It is a literal-plus-edge test, fully
evaluable, so the sweep's protective carve-out does not cover it and the
mechanical verdict on a failing card is *strip*.

## What's broken

Both clauses of the row describe properties an umbrella acquires
*incidentally*, and neither follows from being an umbrella:

- **The literal clause** depends on the author writing the string
  `meta-fix` somewhere in the card. This repo does not name umbrellas that
  way. It names them by shape — `…-and-keeps-drifting`,
  `…-keep-spawning-…-fixes`, `…-is-opt-in-per-…-and-new-…-keep-missing-it`,
  `…-reimplement-…-and-drift`. None of those conventions contains the word.
- **The edge clause** depends on the family already being wired. An umbrella
  is filed *because* a family was noticed; the roster is wired later, and for
  some umbrellas never, because the family members are code sites rather than
  cards.

At filing time a correctly-tagged umbrella therefore satisfies neither
clause. It is born failing its own row, and stays failing until someone
happens to write the word or wire an edge.

Two of the four current failures are exactly that: filed after the row was
widened, both by the shape convention, both zero-edge.

The remaining two show the condition persists rather than self-correcting.
`frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`
carries ten edges and still fails, because the edge clause requires the
*neighbour* to be tagged and its ten neighbours are the per-site instances,
not siblings. `ship-game-of-cards-as-cross-agent-cli` carries eighteen.
Edge count is not the discriminator the clause assumes it is.

## Empirical evidence

`reproduce.py` applies the row verbatim to the live tagged population,
reading each card through the engine's own parser (`card.body` has the
frontmatter split off, so a card cannot satisfy its own row merely by
carrying the tag):

```
deck: /home/runner/work/game-of-cards/game-of-cards/.game-of-cards/deck
`meta-fix`-tagged cards: 105 total, 54 live (open/active)

4 live card(s) carry `meta-fix` and fail the row's own predicate:
  - a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach
      created=2026-07-30  gate=decision  edges=0
  - frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting
      created=2026-06-18  gate=decision  edges=10
  - ship-game-of-cards-as-cross-agent-cli
      created=2026-05-03  gate=session  edges=18
  - static-source-guards-never-prove-they-can-catch-an-offender
      created=2026-07-27  gate=decision  edges=0

FAIL: Skill(refine-deck) § 'Tags without firing predicates' strips a tag
where its row plainly fails, so the sweep is pointed at the umbrella
grouping the tag exists to provide.
```

All four are umbrellas by inspection, and the two zero-edge ones are also
what refine-deck's orphaned-dependency sub-check 2 surfaces — where the
prescribed disposition for a zero-edge card with no literal is likewise
*strip*. Two independent sub-checks converge on the same wrong answer for
the same cards.

**The closing verification was tautological.** The predecessor card closed on
"all 45 open tagged cards pass with zero false positives". Replaying the row
against the deck at that card's own closure commit (`e6b85018`, 2026-07-08)
through the engine's parser finds the same population — 45 open tagged
cards — and fails 5 of them. Three of the five
(`openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting`,
`extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate`,
`codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync`)
are the very cards that card's evidence section named as the umbrellas the
widening was meant to rescue.

The reason the original sweep saw zero is recoverable from its own log entry,
which reports the clause breakdown as "**45/45** via body-wide literal":

> ran the widened predicate over all 45 open `meta-fix`-tagged cards (script
> over `goc --tag meta-fix --status open --json` + per-card README read)

A **README read** is the whole file, frontmatter included — and every
`meta-fix`-tagged card contains the literal `meta-fix` in its own `tags:`
line. The literal clause therefore fired on 45 of 45 by construction. The
check could not have failed for any card in the population it selected, which
is why its result is exactly the population size, and why the regression went
26 days unnoticed. Searching `card.body`, which the engine hands over with
the frontmatter already split off, is the whole difference between that run
and this one.

This is the defect class stated by
[static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
— a check with two passing states that cannot tell them apart — landing on
the verification of a tag row, and that card is itself one of the four the
row now fails.

## Why it matters

This is the third occurrence of the same shape in the same table:

| date | row | measured failure | resolution |
|---|---|---|---|
| 2026-07-08 | `meta-fix` | 37 of 45 (window too narrow) | widen the row |
| 2026-07-27 | `story` | 67 of 102 (unsatisfiable branch) | widen the row |
| 2026-08-03 | `meta-fix` | 4 of 54 (unsatisfiable at filing) | — |

The predecessor card already recorded the hypothesis this is evidence for:

> Nothing here is invalidated — the `meta-fix` row is still correct and
> still verified; the new card is evidence that one row at a time may be
> the wrong unit of repair for this table.

Two widenings later the same row fails again, by a mechanism widening does
not address: the previous fix enlarged the *surface* the literal is searched
in, and the problem is that there is no literal to find. A third widening of
the same kind buys the same 26 days.

The cost is not a mislabelled card. It is that the mechanical hygiene path is
aimed at the curated grouping the tag exists to provide: `goc --tag meta-fix`
is how a reader finds the umbrella population, and the four cards a
compliant sweep would strip are four of the umbrellas. Stripping is silent
and nothing downstream flags the loss — the same asymmetry
`reference.md` § "Tag sweeps" already names as the larger of the two failure
modes, arriving through the row it classified as safe to act on.

This pass declined the strip and filed instead. That is a judgment call by
one agent, not a property of the contract; the next pass reading the same
row gets the same instruction.

## Fix

Not applied. Three shapes, in increasing order of cost — the second is
recommended, and the third is the one the recurrence argues for:

1. **Widen the row again**, adding the umbrella title conventions as
   satisfiers. Smallest diff, matches the two precedents, and fails the same
   way: it enumerates the shapes that exist today, so the next convention is
   unprotected. This is the option the third occurrence argues against.
2. **Give the row a satisfier an umbrella meets by construction** — for
   example a frontmatter-level marker the author sets when filing an
   umbrella, so the tag's meaning stops depending on prose archaeology.
   Removes the birth condition rather than patching its instances.
3. **Make the sweep non-destructive on a failing row.** Change the
   mechanical action from *strip* to *report*, so a predicate that
   under-fires costs a line of output rather than curated data. This is
   orthogonal to which predicate is chosen and bounds every future
   occurrence of the shape, including on rows nobody has measured yet.
   `reference.md` § "Tag sweeps" already argues the asymmetry that motivates
   it; only the instruction did not follow.

Whichever is picked, the `story` card's closure is the precedent for scope:
fixing the row alone did not hold, because `Skill(refine-deck)` restates the
tag contract inline and had to be corrected in the same pass. Both the skill
body and its `reference.md` are in scope here for the same reason.

## Cross-references

- [meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag](../meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag/)
  — the 2026-07-08 widening this card measures the aftermath of, and the
  source of the "wrong unit of repair" hypothesis.
- [story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it](../story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it/)
  — the second occurrence, on a different row, resolved the same way; also
  where the sweep was changed to defer to each row's own predicate.
- [static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
  — one of the four failing cards, and the root statement of the defect class
  the predecessor's tautological closing check belongs to. That card's
  § "A fourth surface" records this instance and what it adds to its open
  scope decision: both of its options attach to scanners in `tests/`, and a
  card's one-shot closure sweep is neither.
- [a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach](../a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach/)
  — another of the four; documents what a tag grouping costs when it is the
  only grouping, which is what the strip would leave behind.

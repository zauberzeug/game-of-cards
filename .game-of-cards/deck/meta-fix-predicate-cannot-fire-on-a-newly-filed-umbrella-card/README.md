---
title: meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card
summary: "RESOLVED (classified, 2026-08-03): the `meta-fix` row fired on a literal in the title, `summary:` or body, or on an edge to another `meta-fix`-tagged card — properties an umbrella acquires incidentally and late, so a freshly filed umbrella satisfied neither clause and scored as mistagged while `Skill(refine-deck)`'s documented action was to strip the tag. Third occurrence of the shape on the same table, so the repair is not a third widening: the canonical-tags table now declares a `check` class per row — `state` (satisfied out of frontmatter, edges, or card files; scorable) or `judgment` (satisfied by what the card means; the row's patterns are recognition aids, not a membership test) — `meta-fix` is `judgment`, and the sweep's action on any non-firing row is report, never strip. `tests/test_canonical_tag_rows.py` scores the live population against every `state` row in CI and carries offender cases proving the scorers still discriminate."
status: done
stage: null
contribution: low
created: "2026-08-03T02:48:05Z"
closed_at: "2026-08-03T05:47:50Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [documentation, bug]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — every live `meta-fix`-tagged card satisfies the row as written. — the row as rewritten is a `judgment` row, so there is nothing to score and every umbrella satisfies it by construction; `reproduce.py` asserts the two properties that make the old failure impossible (row classified `judgment`, no strip instruction in the sweep) and still prints the population the original predicate cannot fire on, which stays non-empty by design. Verified failing at the pre-fix state.
  - [x] PROCESS: pick the unit of repair and record the reasoning in `log.md` — widen this row a second time, give the table a shared satisfier that umbrella-shaped cards meet by construction, or make the sweep non-destructive on a failing row. The third recurrence is the evidence the row is the wrong unit; see `## Fix`. — picked options 2 + 3, with option 2 taken as a table-level classification rather than a new frontmatter marker; reasoning and the rejected forms in log.md.
  - [x] MECHANICAL: the chosen wording lands in `goc/templates/skills/card-schema/SKILL.md` (source of truth; mirrors regenerate via the sync hook), and `Skill(refine-deck)` § "Tags without firing predicates" plus `reference.md` § "Tag sweeps" stay consistent with it — the `story` card's closure showed fixing the row alone does not hold, because the sweep restates the contract inline. — all four surfaces updated, plus two more inline restatements the DoD did not name (orphaned-dependency sub-check 2 and the Step 4.5 mechanical-apply list).
  - [x] TDD: a regression test scores the live tagged population against the row and fails when a card carrying a tag cannot satisfy it, so the next drift is caught by CI instead of by the next refine pass. — `tests/test_canonical_tag_rows.py`, 8 cases: per-row `check` declaration, table/enum parity, row-to-scorer lockstep, live-population scoring, offender recall, `meta-fix` stays `judgment`, and the sweep stays non-destructive.
  - [x] MECHANICAL: `uv run goc validate` passes and `python scripts/sync_plugin_assets.py --check` is green. — both green; `port_skills_to_openclaw.py --check` and the 897-test suite too.
worker: {who: "claude[bot]", where: main}
---

# The `meta-fix` predicate cannot fire on a newly filed umbrella card

## Location

`goc/templates/skills/card-schema/SKILL.md` § "Canonical tags" (mirrored to
`.claude/skills/card-schema/SKILL.md`), the `meta-fix` row as widened by
[meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag](../meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag/)
on 2026-07-08:

```
| `meta-fix` | literal `meta-fix` / `family meta-fix` in title, `summary:`, or full body (no cutoff), OR an `advances`/`advanced_by` edge to a `meta-fix`-tagged card |
```

The consumer was `Skill(refine-deck)` § "Tags without firing predicates",
which instructed the operator to "strip only where a row plainly fails", and
its `reference.md` § "Tag sweeps", which classified rows into judgment rows
(leave alone) and text-matchable rows (act on):

> **Inability to evaluate a row is not evidence the row fails.** Some rows
> turn on a judgment about what the card delivers or touches [...] and have
> no closed-form text predicate at all. There is nothing to grep. Leave
> these unless the card plainly contradicts the row.

`meta-fix` was not one of those. It was a literal-plus-edge test, fully
evaluable, so the sweep's protective carve-out did not cover it and the
mechanical verdict on a failing card was *strip*.

## What was broken

Both clauses of the row described properties an umbrella acquires
*incidentally*, and neither followed from being an umbrella:

- **The literal clause** depended on the author writing the string
  `meta-fix` somewhere in the card. This repo does not name umbrellas that
  way. It names them by shape — `…-and-keeps-drifting`,
  `…-keep-spawning-…-fixes`, `…-is-opt-in-per-…-and-new-…-keep-missing-it`,
  `…-reimplement-…-and-drift`. None of those conventions contains the word.
- **The edge clause** depended on the family already being wired. An umbrella
  is filed *because* a family was noticed; the roster is wired later, and for
  some umbrellas never, because the family members are code sites rather than
  cards.

At filing time a correctly-tagged umbrella therefore satisfied neither
clause. It was born failing its own row, and stayed failing until someone
happened to write the word or wire an edge.

Two of the four failures measured at filing were exactly that: filed after
the row was widened, both by the shape convention, both zero-edge.

The rest showed the condition persists rather than self-correcting.
`frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`
carries ten edges and still failed, because the edge clause required the
*neighbour* to be tagged and its ten neighbours are the per-site instances,
not siblings. `ship-game-of-cards-as-cross-agent-cli` carries eighteen.
Edge count was not the discriminator the clause assumed it was.

## Empirical evidence

`reproduce.py` still applies the original row verbatim to the live tagged
population, reading each card through the engine's own parser (`card.body` has
the frontmatter split off, so a card cannot satisfy its own row merely by
carrying the tag):

```
`meta-fix`-tagged cards: 105 total, 54 live (open/active)

3 live card(s) the ORIGINAL literal-plus-edge predicate cannot fire on:
  - a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach
      created=2026-07-30  gate=decision  edges=0
  - frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting
      created=2026-06-18  gate=decision  edges=10
  - ship-game-of-cards-as-cross-agent-cli
      created=2026-05-03  gate=session  edges=18
```

Three, not the four measured at filing:
`static-source-guards-never-prove-they-can-catch-an-offender` started passing
in between, because a cross-reference to *this* card put the literal
`meta-fix` into its body. A row a card can start satisfying because a
neighbour was filed is the incidental-property problem in one observation.

All are umbrellas by inspection, and the two zero-edge ones were also what
refine-deck's orphaned-dependency sub-check 2 surfaced — where the prescribed
disposition for a zero-edge card with no literal was likewise *strip*. Two
independent sub-checks converged on the same wrong answer for the same cards.

**The closing verification of the predecessor was tautological.** That card
closed on "all 45 open tagged cards pass with zero false positives". Replaying
the row against the deck at its own closure commit (`e6b85018`, 2026-07-08)
through the engine's parser finds the same population — 45 open tagged cards —
and fails 5 of them. Three of the five
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
is why its result was exactly the population size, and why the regression went
26 days unnoticed. Searching `card.body`, which the engine hands over with
the frontmatter already split off, is the whole difference between that run
and this one.

This is the defect class stated by
[static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
— a check with two passing states that cannot tell them apart — landing on
the verification of a tag row, and that card is itself one of the umbrellas
the row failed at filing. The regression test added here answers it directly:
its `OFFENDERS` table makes each scorer demonstrate it still rejects a
violating card, so a scorer that stopped discriminating fails rather than
reporting a clean deck.

## Why it matters

This was the third occurrence of the same shape in the same table:

| date | row | measured failure | resolution |
|---|---|---|---|
| 2026-07-08 | `meta-fix` | 37 of 45 (window too narrow) | widen the row |
| 2026-07-27 | `story` | 67 of 102 (unsatisfiable branch) | widen the row |
| 2026-08-03 | `meta-fix` | 4 of 54 (unsatisfiable at filing) | classify the rows |

The predecessor card already recorded the hypothesis this is evidence for:

> Nothing here is invalidated — the `meta-fix` row is still correct and
> still verified; the new card is evidence that one row at a time may be
> the wrong unit of repair for this table.

Two widenings later the same row failed again, by a mechanism widening does
not address: the previous fix enlarged the *surface* the literal is searched
in, and the problem was that there is no literal to find. A third widening of
the same kind buys the same 26 days.

The cost was not a mislabelled card. It was that the mechanical hygiene path
was aimed at the curated grouping the tag exists to provide: `goc --tag
meta-fix` is how a reader finds the umbrella population, and the cards a
compliant sweep would strip were umbrellas. Stripping is silent and nothing
downstream flagged the loss — the same asymmetry `reference.md` § "Tag sweeps"
already named as the larger of the two failure modes, arriving through the row
it classified as safe to act on.

The pass that filed this card declined the strip. That was a judgment call by
one agent, not a property of the contract; the contract now agrees with it.

## Resolution

Options 2 and 3 from the filing, together. Not a third widening — that is the
option the third occurrence argues against, and it does not reach a card whose
whole subject is a deliberately edgeless grouping.

**The table declares a `check` class per row** (option 2, taken as a
table-level classification rather than the new frontmatter marker the filing
floated — see log.md for why that form was rejected):

- **`state`** — the satisfier is readable out of frontmatter, edge arrays, or
  files in the card directory: `bug`, `epic`, `unverified`. Scorable, so a
  disagreement is a fact, and CI now scores them.
- **`judgment`** — the satisfier is what the card *means*: `story`,
  `documentation`, `test`, `api-contract`, `infra`, `meta-fix`. The patterns
  printed in those rows are **recognition aids**, not a membership test, so a
  pattern that does not fire is not evidence the tag fails.

`meta-fix` is `judgment`, and its row now states the property it actually
asserts — the card's scope is a family or its root cause rather than a single
site — with the literal, the roster, and the edge demoted to aids marked
**none required**. An umbrella meets that by being an umbrella, which removes
the birth condition instead of patching its instances.

**The sweep's action on any non-firing row is `report`** (option 3). Stripping
is a deliberate per-card judgment, recorded as such, never the mechanical
consequence of a predicate that did not fire. This half is orthogonal to which
predicate is chosen and bounds every future occurrence of the shape, including
on rows nobody has measured — an under-firing row now costs a line of output
instead of curated data.

Landed in:

- `goc/templates/skills/card-schema/SKILL.md` § "Canonical tags" — the
  `check` column and the two-line rule.
- `goc/templates/skills/card-schema/reference.md` § "Why rows split" — the
  three measurements, the default aid surface, and the `check` requirement for
  any new row.
- `goc/templates/skills/refine-deck/SKILL.md` — "Report, never strip" in the
  sweep, the hygiene-findings carve-out, and the code-sites branch on
  orphaned dependencies.
- `goc/templates/skills/refine-deck/reference.md` § "Tag sweeps" — three rules
  instead of two, with `meta-fix` as the cautionary example rather than the
  evaluable one; sub-check 2's strip fork replaced by three dispositions of
  which only one edits YAML; the Step 4.5 note and the Step 4 example output.
- `tests/test_canonical_tag_rows.py` — the CI guard.
- `tests/test_skill_body_size.py` — two hot-path caps raised for the added
  contract text, with the reason in the constant's comment.

## Cross-references

- [meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag](../meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag/)
  — the 2026-07-08 widening this card measures the aftermath of, and the
  source of the "wrong unit of repair" hypothesis.
- [story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it](../story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it/)
  — the second occurrence, on a different row, resolved the same way; also
  where the sweep was changed to defer to each row's own predicate.
- [static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
  — one of the umbrellas the row failed, and the root statement of the defect
  class the predecessor's tautological closing check belongs to. Its
  § "A fourth surface" records this instance; the `OFFENDERS` table in
  `tests/test_canonical_tag_rows.py` is another scanner satisfying its
  requirement, and one that lives in `tests/` where both of that card's open
  options attach.
- [a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach](../a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach/)
  — another; documents what a tag grouping costs when it is the only
  grouping, which is what the strip would have left behind.

---
title: story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it
summary: "RESOLVED (widened, 2026-07-27): the card-schema tag table defined `story` as 'part of an epic-grouping (carries the epic-grouping tag)' — a satisfier no card in this repo could meet, because `.game-of-cards/canonical-tags.md` is an empty stub — so 67 of 102 `story`-tagged cards (66%) scored as mistagged and a mechanical refine-deck sweep would have stripped them. Measured against the deck, `story` and `bug` are disjoint (1 card of 681 carried both) and the failing cards are capability deliveries, so the row was widened to its observed meaning — delivers new or changed capability rather than fixing something already broken — with epic membership demoted to an orthogonal property recorded by edges. Following the `meta-fix` precedent: widen to match practice, do not re-tag the deck. refine-deck's sweep now defers to each row's own predicate instead of the ~2500-char window."
status: done
stage: null
contribution: low
created: "2026-07-27T02:49:48Z"
closed_at: "2026-07-27T04:42:48Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [documentation, bug]
definition_of_done: |
  - [x] PROCESS: pick the resolution — widen the `story` predicate in the card-schema tag table to match observed deck practice, re-tag the deck to comply, or register an epic-grouping tag so the unreachable branch becomes reachable — and record the reasoning in log.md. — picked **widen**, following the `meta-fix` precedent; reasoning in log.md.
  - [x] TDD: `reproduce.py` exits zero — every `story`-tagged card satisfies the predicate as written. — rewritten to score the widened row; exits 0.
  - [x] MECHANICAL: the chosen predicate wording lands in `goc/templates/skills/card-schema/SKILL.md` (source of truth; mirrors regenerate via the sync hook), and the parenthetical "(carries the epic-grouping tag)" is either made accurate or dropped. — dropped from the row outright; epic-grouping tags survive only in the `epic` row and in `reference.md`, as one of two ways to record orthogonal membership.
  - [x] MECHANICAL: if the resolution keeps the tag branch, `.game-of-cards/canonical-tags.md` documents at least one epic-grouping tag with its predicate — a branch nothing can satisfy is not a branch. — N/A: the resolution removes epic-grouping from the `story` row's satisfier set, so nothing needed registering; canonical-tags.md stays an empty stub.
  - [x] MECHANICAL: `uv run goc validate` passes and `python scripts/sync_plugin_assets.py --check` is green.
worker: {who: "claude[bot]", where: main}
---

# The `story` tag predicate fails on two thirds of the cards carrying it

## Location

`goc/templates/skills/card-schema/SKILL.md` § "Canonical tags" (mirrored to
`.claude/skills/card-schema/SKILL.md:250`), the tag-application table **as
filed**:

```
| tag | applies iff |
|---|---|
| `bug` | not `epic` and not `story` (default for findings) |
| `epic` | multiple cards block its closure OR carry its epic-grouping tag |
| `story` | part of an epic-grouping (carries the epic-grouping tag) |
```

governed by the rule stated two lines above it:

> A tag is **load-bearing** iff its predicate fires on the title, H1, or first
> ~2500 chars of body (unless its row widens the surface); when in doubt, drop
> it.

`Skill(refine-deck)` § "Tags without firing predicates" turns that rule into a
recurring mechanical action: "for any tag whose predicate doesn't fire, strip
it (mechanical frontmatter edit)."

## What was broken

The `story` predicate had one stated satisfier — carrying the epic-grouping
tag — and in this repo nothing can carry one.

`.game-of-cards/canonical-tags.md`, the file `goc validate` merges into the tag
enum, is an unedited stub: its entire content is the scaffold comment ending
"If this file is empty, the skills proceed with their generic flow." So the
deck's whole tag vocabulary is the nine tags goc ships — `bug`, `epic`,
`story`, `unverified`, `documentation`, `test`, `api-contract`, `infra`,
`meta-fix` — and none of them is an epic-grouping tag. The branch is not
merely unused; it is unsatisfiable until someone registers a tag.

The deck expresses epic membership the other way, through edges. That reading
is the one `Skill(create-card)` teaches — "Aggregation epic (closes when its
children close) → `child.advances: [epic]`" — and it is the only branch any
card here can satisfy. Scored against it, 35 of 102 `story` cards pass and 67
fail.

The sibling card [no-guardrail-for-canonical-epic-edge-direction](../no-guardrail-for-canonical-epic-edge-direction/)
already recorded the underlying observation from the other side, at
`README.md:176-180`:

> The faithful encoding of "govern but don't block" is a **tag** — zero value
> flow, zero closure gating. card-schema already allows this: the `epic` tag is
> "multiple cards block it from closing **OR** carry the same epic-grouping
> tag." The gap is the *OR* is never surfaced, so authors reach for an edge
> even when a tag is the honest tool.

That card noted the tag branch goes unused. This one measures what the unused
branch costs the `story` row, where it is not one of two options but the only
one written down.

## Empirical evidence

At filing time `reproduce.py` scored every `story`-tagged card against both
branches of the row as written and exited 1 while any card satisfied neither.
That run — the finding, preserved; the script has since been rewritten to score
the widened row and now exits 0 (see § Resolution):

```
$ uv run python .game-of-cards/deck/story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it/reproduce.py
epic-tagged cards:            11
epic-grouping tags available: (none)
story-tagged cards:           102
  predicate fires:            35
  predicate does NOT fire:    67

FAIL — 67/102 (66%) `story`-tagged cards satisfy neither branch of the predicate.

Non-terminal offenders (the ones a hygiene sweep would strip):
  open    audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings
  open    derive-openclaw-manifest-skills-array-from-ported-skill-dirs
  active  list-game-of-cards-on-anthropic-community-marketplace  <- 11 cards block its closure; the `epic` predicate fires
  active  openclaw-plugin-skills-force-repeated-reads-every-session
  open    parallel-agents-double-close-cards-because-claim-protections-are-disabled
  open    support-custom-frontmatter-fields-with-enum-and-required-when-rules
```

Two entries in that list sharpen the finding beyond a bare count:

- **[list-game-of-cards-on-anthropic-community-marketplace](../list-game-of-cards-on-anthropic-community-marketplace/)**
  carries 11 `advanced_by` blockers. The `epic` predicate ("multiple cards
  block its closure") fires on it outright while the `story` predicate it is
  actually tagged with fires on nothing. One card, same table, opposite
  verdicts — the clearest single case that the rows do not partition the deck
  the way the deck is filed.
- **[support-external-game-of-cards-state-location](../support-external-game-of-cards-state-location/)**
  carries `epic` *and* `story` together. Under the documented predicates it
  would have to be a member of its own grouping.

Sixty-one of the 67 are terminal (55 `done`, 3 `superseded`, 3 `disproved`), so
the live blast radius of a strip sweep is the six above. The record axis is the
larger share, and it matters: the deck is scheduler **and** record, and the
`story` tag is how a reader browsing closed work reconstructs which cards
belonged to which push.

## Why it matters

This is the second measured instance of one shape: a card-schema tag predicate
that scores most of its own population as mistagged.

The first was [meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag](../meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag/)
(closed 2026-07-08), where the strict title/H1/first-~2500-chars window failed
on 37 of 45 open `meta-fix` cards. Its resolution is the precedent worth
reading before picking one here: the predicate was **widened to match observed
practice** — literal anywhere in title, `summary:` or full body, or an edge to
a `meta-fix`-tagged card — rather than the deck being re-tagged to comply.
Same shape, same table, same failure mode; only the row differs. Neither card
delivers the other's value, so the link is a cross-reference and not an
`advances` edge.

The concrete cost is that `Skill(refine-deck)`'s "tags without firing
predicates" sweep is unrunnable on the `story` row. An agent applying the
documented rule mechanically — which is exactly what the skill instructs, on
every hygiene pass — strips two thirds of a tag the deck plainly uses on
purpose. That is why the present pass filed this card instead of stripping the
six live tags: the predicate is the thing that looks wrong, not the cards.

## Resolution — widened, matching the `meta-fix` precedent

**Picked option 1 (widen), and widened further than option 1 proposed.** The
three options below were the filed menu; what the deck measures says option 1
as drafted was still too narrow, so the row was widened past epic-grouping
altogether.

### What the deck says `story` means

Two measurements over all 681 cards decided it:

- **`story` and `bug` are disjoint.** Exactly one card of 681 carried both
  (`plugin-install-doesnt-refresh-stale-marketplace-cache`, `done`). The two
  tags are used as a partition — 482 `bug`, 102 `story`, 89 carrying neither.
- **The 67 "failing" cards are capability deliveries.** Reading them, they are
  `add-worker-field-and-filter-to-cards`,
  `cli-output-suggests-next-step-after-each-verb`,
  `derive-claude-hook-manifest-from-templates`, `install-claude-harness`,
  `create-project-website-explanatory-illustration` — additive work, not defect
  findings. Nothing about them is mistagged.

So the tag's real meaning is *what kind of work the card delivers*, and the
`bug` row already said as much from the other side ("not `epic` and not
`story` (default for findings)"). The old row's defect was naming a **grouping
mechanism** as the **definition** of the tag. Epic membership is a genuine but
separate property, and the deck records it with edges.

Two anomalies the filing flagged dissolve under this reading rather than
needing fixes: `support-external-game-of-cards-state-location` and
`drop-third-party-runtime-dependencies-from-goc` carry `epic` *and* `story`,
which is coherent once `story` stops meaning "member of a grouping" — an epic
can itself be a capability delivery with children. And
[list-game-of-cards-on-anthropic-community-marketplace](../list-game-of-cards-on-anthropic-community-marketplace/),
where the `epic` predicate fired but `story` did not, now satisfies both rows
honestly.

### What changed

Both hot-path `SKILL.md` files sit within a few bytes of the size caps in
`tests/test_skill_body_size.py` (card-schema 11988/12000, refine-deck
9997/10000), and that guard's stated contract is that new nuance belongs in
the sibling `reference.md`, not the core. So each change is a terse row or
sentence in `SKILL.md` plus the reasoning in `reference.md` — the split the
cap exists to force, not a workaround for it.

- `goc/templates/skills/card-schema/SKILL.md` — the `story` row now reads
  "delivers new/changed capability, not a fix; disjoint from `bug`". The
  parenthetical "(carries the epic-grouping tag)" is dropped outright: with
  grouping no longer a satisfier, the row has no reason to mention it. The
  `bug` and `epic` rows are unchanged — `bug`'s exclusion form stops being
  circular now that `story` carries positive content, and `epic`'s
  grouping-tag branch is correct for consumer repos that register one.
- `goc/templates/skills/card-schema/reference.md` — new § "The `bug` /
  `story` / `epic` rows": the two questions the rows answer, why `epic` +
  `story` together is legitimate, why membership is recorded by edges and is
  not a condition of the tag, and why cards carrying neither `bug` nor `story`
  are fine.
- `goc/templates/skills/refine-deck/SKILL.md` § "Tags without firing
  predicates" — **the fix does not hold without this.** That section restated
  the strict title/H1/~2500-char window inline and told the operator to strip
  any tag that fails it, so a hygiene sweep would have stripped `story` no
  matter what the card-schema row said. It now scores each tag against its own
  row and points at the reference sibling. (It had also drifted from
  card-schema's "unless its row widens the surface" escape hatch, added by the
  `meta-fix` precedent and never mirrored here.)
- `goc/templates/skills/refine-deck/reference.md` — new § "Tag sweeps"
  carrying the two rules the sweep needs: score against the row, not a house
  rule; and inability to evaluate a row is not evidence the row fails. Names
  the judgment rows (`story`, `api-contract`, `infra`) that have no text
  predicate at all, and gives the one `story` case that *is* a real finding —
  a card carrying `bug` too.
- `plugin-install-doesnt-refresh-stale-marketplace-cache` — `story` stripped,
  the single card contradicting the now-explicit partition. Its deliverable is
  a documented workaround for a third-party defect; `bug` is the right row.
- `reproduce.py` — rewritten to score the widened row. It gates on the
  mechanically decidable half (no card carries both `story` and `bug`, asserted
  by *both* rows) and reports epic-grouping coverage without gating on it,
  because gating on an orthogonal property is the original defect. Exits 0.

### Why not options 2 or 3

**Option 2 (re-tag the deck)** would strip a tag from 67 cards that are
correctly tagged under the meaning the deck actually uses. It treats a
documentation defect as a data defect — the same inversion the `meta-fix`
precedent rejected.

**Option 3 (register an epic-grouping tag)** is not required by this row once
grouping stops being a satisfier, and it is a separate curation decision about
this deck's vocabulary, not a fix to a wrong predicate. It stays available and
undamaged: the `epic` row still offers the branch, and the candidate-grouping
table below is preserved as its input. Deliberately declined here rather than
bundled — see log.md.

### The filed menu, for the record

As drafted at filing time. Option 1 was picked and then widened further, for
the reason given above: as written it still failed the 67, because it kept
epic-grouping as the satisfier and only added the edge branch — which is
exactly what the original `reproduce.py` already scored (35/102).

1. **Widen the predicate** (what `meta-fix` did): `story` applies iff the card
   carries an epic-grouping tag **OR** has an `advances` / `advanced_by` edge
   to an `epic`-tagged card. Retroactively correct for the 35 that already
   pass; still fails the 67, so it needs pairing with a scope call on whether
   unwired closed cards keep the tag as a record marker.
2. **Re-tag the deck**: strip `story` from the 67, wire the six live ones into
   an epic where one exists. Honest to the table as written, but discards
   record-axis grouping on 61 closed cards and contradicts the precedent's
   resolution.
3. **Register an epic-grouping tag**: give `.game-of-cards/canonical-tags.md`
   at least one real grouping tag so the documented branch becomes reachable,
   and let existing edge-linked stories keep passing under a widened row. Most
   faithful to the original design intent recorded in
   [no-guardrail-for-canonical-epic-edge-direction](../no-guardrail-for-canonical-epic-edge-direction/);
   the most work.

The menu's one non-negotiable — that the parenthetical "(carries the
epic-grouping tag)" stop being the only stated satisfier of a predicate no card
in this repo could satisfy — was met: it is no longer a satisfier at all.

### Input for option 3: the groupings the deck already has, unnamed

The same refine-deck pass ran Step 3 (new canonical tag candidates) and found
no cluster that an existing tag fails to *cover* — every one of these is
legitimately `infra` — but several that no tag **groups**. Title-substring
counts over all 679 cards:

| candidate grouping | cards | open/active |
|---|---|---|
| `plugin` | 58 | 14 |
| `hook` | 52 | 7 |
| `openclaw` | 40 | 14 |
| `release` | 25 | 6 |
| `codex` | 17 | 6 |
| `yaml-lite` | 16 | 1 |

Substring counts overlap (`openclaw` cards are mostly `plugin` cards too) and
are a lower bound on the real clusters, so treat the table as a starting point
for the scope call, not a proposed tag list. What it establishes is that
option 3 is not hypothetical: there are coherent multi-dozen-card bodies of
work here, they are exactly what a reader browsing closed work wants to group
by, and the reason none is tagged is that registering one has never been on
anyone's path. Step 3 deliberately filed no separate tag-proposal card — the
proposal is the same decision as this card's option 3, and splitting it would
have produced two cards with one root cause.

## Post-closure: this row is now classified, and the sweep no longer strips

On 2026-08-03 the `meta-fix` row failed a third time, by a mechanism no
widening reaches, and the repair moved up a level — see
[meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card](../meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card/).
Every row in the canonical-tags table now declares a `check` class, and
`story` is `judgment`: its "delivers new or changed capability" satisfier is
exactly the kind this card widened the row *to*, and the classification makes
that explicit rather than leaving it as prose a sweep could mis-score.

Two claims in the resolution above are narrowed by that. The sweep deferring
to each row's own predicate is still the contract, but it no longer *acts* on
the result — a non-firing row is reported, never stripped, so the
mass-stripping scenario this card measured is now impossible rather than
merely unlikely. And the widening precedent this card cites from the
`meta-fix` row is retired: widening is no longer the standard answer to a row
that under-fires, because it was the answer twice and the shape recurred both
times.

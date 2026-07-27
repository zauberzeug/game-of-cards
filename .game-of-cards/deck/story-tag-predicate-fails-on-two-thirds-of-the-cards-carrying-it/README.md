---
title: story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it
summary: "The card-schema tag table defines `story` as 'part of an epic-grouping (carries the epic-grouping tag)', but 67 of the 102 `story`-tagged cards in this deck (66%) have no edge to any `epic`-tagged card, and the predicate's tag branch is unreachable here because `.game-of-cards/canonical-tags.md` is an empty stub — the deck uses only the nine goc-shipped tags, none of which is an epic-grouping tag. A mechanical refine-deck sweep applying the documented predicate would strip `story` from two thirds of the cards carrying it, so the predicate needs the same widen-or-retag scope decision that `meta-fix` already got."
status: open
stage: null
contribution: low
created: "2026-07-27T02:49:48Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation, bug]
definition_of_done: |
  - [ ] PROCESS: pick the resolution — widen the `story` predicate in the card-schema tag table to match observed deck practice, re-tag the deck to comply, or register an epic-grouping tag so the unreachable branch becomes reachable — and record the reasoning in log.md.
  - [ ] TDD: `reproduce.py` exits zero — every `story`-tagged card satisfies the predicate as written.
  - [ ] MECHANICAL: the chosen predicate wording lands in `goc/templates/skills/card-schema/SKILL.md` (source of truth; mirrors regenerate via the sync hook), and the parenthetical "(carries the epic-grouping tag)" is either made accurate or dropped.
  - [ ] MECHANICAL: if the resolution keeps the tag branch, `.game-of-cards/canonical-tags.md` documents at least one epic-grouping tag with its predicate — a branch nothing can satisfy is not a branch.
  - [ ] MECHANICAL: `uv run goc validate` passes and `python scripts/sync_plugin_assets.py --check` is green.
---

# The `story` tag predicate fails on two thirds of the cards carrying it

## Location

`goc/templates/skills/card-schema/SKILL.md` § "Canonical tags" (mirrored to
`.claude/skills/card-schema/SKILL.md:250`), the tag-application table:

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

## What's broken

The `story` predicate has one stated satisfier — carrying the epic-grouping
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

`reproduce.py` in this directory scores every `story`-tagged card against both
branches and exits 1 while any card satisfies neither:

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

## Decision (deferred, gate left at `none`)

The three resolutions below are all cheap; the pick is a scope judgment, not a
blocked question, so the gate stays `none` and the first DoD box carries it.
The next reader may raise the gate if they disagree.

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

Whichever is picked, the parenthetical "(carries the epic-grouping tag)" must
stop being the only stated satisfier of a predicate no card in this repo can
satisfy.

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

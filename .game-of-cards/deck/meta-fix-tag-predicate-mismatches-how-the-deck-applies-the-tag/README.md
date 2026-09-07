---
title: meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag
summary: "RESOLVED (widened, 2026-07-08): the `meta-fix` tag predicate in the card-schema skill's tag-application table failed on 37 of 45 open tagged cards — the strict title/H1/first-~2500-chars window never consulted the `summary:` field, the full body, or the edge graph, so a mechanical hygiene sweep would have stripped tags from correctly-wired families. The predicate now fires on a literal `meta-fix` anywhere in the title, `summary:` field, or full body, OR a non-empty edge to a `meta-fix`-tagged card; the intro was reworded to make the ~2500-char window a per-row-overridable default, and refine-deck's zero-edge sub-check now routes its genuine-vs-mistagged judgment through the same predicate. Verified: all 45 open tagged cards pass with zero false positives."
status: done
stage: null
contribution: low
created: "2026-07-06T01:30:52Z"
closed_at: "2026-07-08T01:07:09Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, bug]
definition_of_done: |
  - [x] PROCESS: pick the resolution — widen the `meta-fix` predicate in the card-schema skill's tag-application table to match observed deck practice, or keep the strict window predicate and re-tag the deck to comply — and record the reasoning in log.md.
  - [x] MECHANICAL: the chosen predicate wording lands in `goc/templates/skills/card-schema/SKILL.md` (source of truth; mirrors regenerate via the sync hook), and the refine-deck skill's zero-edge sub-check comment stays consistent with it.
  - [x] EMPIRICAL: re-running the predicate sweep from Skill(refine-deck) Step 2 over the open meta-fix-tagged cards yields zero false positives under the updated contract (spot-check documented in log.md).
  - [x] MECHANICAL: `uv run goc validate` passes and `python scripts/sync_plugin_assets.py --check` is green.
worker: {who: "claude[bot]", where: main}
---

# The `meta-fix` tag predicate mismatches how the deck applies the tag

## Evidence

The tag-application contract (card-schema skill, "Tag application
criteria") states:

> A tag is **load-bearing** for a card iff its predicate fires on the
> card's title, H1 title, or first ~2500 chars of body. [...] when in
> doubt, drop the tag.

and the `meta-fix` row's predicate is:

> literal `meta-fix` / `family meta-fix` in title, title, or body

(note the row itself is also typo'd — "title, title, or body").

A 2026-07-06 refine-deck pass tested the literal-in-window predicate
against the open `meta-fix`-tagged population and found it fails on
most of the cards the deck's own conventions treat as correctly
tagged, including **wired family members and heads**:

- `goc-move-leaves-cross-reference-rewrites-uncommitted` — wired into
  the uncommitted-mutation family (`advances:
  goc-repair-edges-apply-leaves-edge-repairs-uncommitted`), literal
  `meta-fix` only deep in the body, outside the ~2500-char window.
- `goc-advance-claims-success-when-adding-an-already-existing-edge` and
  `goc-unadvance-claims-success-when-removing-a-non-existent-edge` —
  both wired (`advances:
  mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success`),
  both fail the window test.
- `pattern-generalization-mutation-detector-misses-compound-and-chained-git-commands`
  — declares its family membership in the `summary:` frontmatter field
  ("the open recognizer-strategy meta-fix"), which the predicate does
  not consult; body literal appears only past the window.
- Umbrella-shaped drift cards
  (`codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync`,
  `single-source-pattern-check-reminder-across-host-ports`,
  `extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate`)
  carry the literal only past the ~2500-char window (the original
  filing claimed zero body-wide literals; a 2026-07-08 re-sweep found
  all three had since gained the literal deep in the body — still
  failing the window test), same architectural class as the
  tagged-and-wired umbrellas
  (`yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`,
  `dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting`).

Meanwhile refine-deck's orphaned-dependency sub-check (Step 2,
"Orphaned dependencies", sub-check 2) tells the operator to judge the
same cards by *role* — "(a) a genuine meta-fix whose family wasn't
wired, or (b) a mistagged instance" — with no reference to the window
predicate. The two categories can return opposite verdicts on the same
card: the predicate sweep says strip, the role judgment says keep and
wire.

## Why it matters

Hygiene passes are meant to be mechanical. A predicate that
under-fires against the deck's real convention makes the mechanical
path destructive (mass-stripping a curated family filter) and forces
per-card judgment calls that the next agent will make differently,
so the tag population drifts with each pass instead of converging.

## Resolution

**The predicate was widened to match practice** (the least-churn of
the three shapes considered: widen; keep-strict and re-tag ~a dozen
cards, weakening the `goc --tag meta-fix` family view; or split the
tag with a schema migration). The `meta-fix` row in the card-schema
skill's tag-application table now fires on a literal `meta-fix` /
`family meta-fix` anywhere in the title, `summary:` frontmatter
field, or full body (no window cutoff), OR a non-empty `advances` /
`advanced_by` edge to a `meta-fix`-tagged card. The table intro was
reworded to make the ~2500-char window a *default* surface that a row
may override (and the row's "title, title, or body" typo fixed).
Refine-deck's zero-edge sub-check comment now routes its
genuine-vs-mistagged judgment through the same predicate: for a
zero-edge card the edge clause can't fire, so the literal test is
decisive — literal present → wire the family; absent → strip.

Empirical verification, **as corrected on 2026-08-03**: the widening
itself was sound — 37 of the 45 open tagged cards fail the old strict
window test and pass the widened row — but the "zero false positives"
figure recorded at closure was produced by a tautological check and is
withdrawn. The sweep searched each card's README *file*; every
`meta-fix`-tagged card carries the literal in its own frontmatter
`tags:` line, so the literal clause fired on 45 of 45 by construction
and no card in the selected population could have failed. Re-running
the row at this card's own closure commit (`e6b85018`) against
`card.body` — the engine's parse, with frontmatter split off — fails
**5 of those same 45**, three of them the umbrella-shaped drift cards
the Evidence section above names as the cards the widening was meant
to rescue. Those three pass today. Tracked in
[meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card](../meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card/).
Original (withdrawn) closure figures in `log.md`.

## Post-closure: the shape recurred on the `story` row

A refine-deck pass on 2026-07-27 measured the same failure mode in the same
table on a different row: the `story` predicate fails on 67 of 102 cards
carrying it. Tracked in
[story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it](../story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it/),
which cites this card's widen-rather-than-re-tag resolution as its precedent.
Nothing here is invalidated — the `meta-fix` row is still correct and still
verified; the new card is evidence that one row at a time may be the wrong
unit of repair for this table.

**Outcome (2026-07-27): resolved the same way, and the "wrong unit of repair"
worry was borne out.** The `story` row was widened to match practice rather
than the deck re-tagged, following this card's precedent. But fixing the row
alone would not have held: `Skill(refine-deck)` § "Tags without firing
predicates" *restated* the strict title/H1/~2500-char window inline and told
the operator to strip on it, so a sweep would have ignored whatever the row
said. That section had never been reconciled with the "unless its row widens
the surface" escape hatch **this** card added — so the `meta-fix` fix was, in
that one respect, also incomplete for two and a half weeks. It now scores each
tag against its own row. The unit of repair for a predicate is the row plus
every place the sweep restates the rule.

## Post-closure: the shape recurred on this row, by a mechanism widening cannot reach

A refine-deck pass on 2026-08-03 measured this row again: 4 of 54 live tagged
cards fail it, two of them filed *after* the widening. Tracked in
[meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card](../meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card/).

The new mechanism is not the one this card fixed. Widening enlarged the
*surface* the literal is searched in; the recurrence is that an umbrella has
no literal to find and no wired family yet, so neither clause of the row can
fire at filing time. This repo names umbrellas by shape
(`…-and-keeps-drifting`, `…-keep-spawning-…-fixes`, `…-is-opt-in-per-…`),
and none of those conventions contains the word. A third widening of the
same kind would not change that.

That pass also re-ran the row at this card's closure commit, which is where
the corrected verification figure above comes from. The two findings compound:
the row under-fires on a shape it exists to name, and the check that was
supposed to notice searched the whole README file — so the frontmatter
`tags:` line satisfied the literal clause for every tagged card and the
result was the population size rather than a measurement. The
"wrong unit of repair" worry recorded above now has a third data point, and
the successor card carries an option this card did not consider — leaving the
predicate alone and making the sweep's action on a failing row non-destructive.

**Outcome (2026-08-03): the row was not widened a third time.** The successor
took the option this card did not consider, plus a bounded form of a second
one. The canonical-tags table now declares a `check` class per row — `state`
(the satisfier is readable out of frontmatter, edges, or card files) or
`judgment` (the satisfier is what the card means, and the row's patterns are
recognition aids rather than a membership test) — and `meta-fix` is
`judgment`, so nothing scores it and an umbrella satisfies it by being one.
The sweep's action on *any* non-firing row is now report, never strip, which
bounds the shape on rows nobody has measured yet.

So this card's widen-rather-than-re-tag resolution is superseded as a
mechanism, not as a diagnosis: the surface was genuinely too narrow, and
enlarging it was the right call for the 37 cards it rescued. What the third
occurrence established is that a row whose satisfier is a *judgment* cannot be
repaired by enlarging a text surface at all, however wide. Three rows of this
table are scored in CI as of the successor's closure
(`tests/test_canonical_tag_rows.py`); `meta-fix` is not one of them, by design.

---
title: meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag
summary: "The card-schema tag contract says a tag is load-bearing iff its predicate fires on title / H1 / first ~2500 chars of body, and the `meta-fix` row's predicate is a literal `meta-fix` in title or body. In this deck most genuinely meta-fix-tagged cards fail that window test — wired family heads and members carry the literal only deep in the body, in the `summary:` frontmatter field, or nowhere at all — so a mechanical predicate sweep would strip tags from correctly-wired families. Either the predicate should be widened to match actual practice (e.g. fire on edge-connection to a tagged family head, the summary field, or body-wide literal) or the convention tightened; today refine-deck's two hygiene categories give contradictory verdicts on the same cards."
status: active
stage: null
contribution: low
created: "2026-07-06T01:30:52Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation, bug]
definition_of_done: |
  - [ ] PROCESS: pick the resolution — widen the `meta-fix` predicate in the card-schema skill's tag-application table to match observed deck practice, or keep the strict window predicate and re-tag the deck to comply — and record the reasoning in log.md.
  - [ ] MECHANICAL: the chosen predicate wording lands in `goc/templates/skills/card-schema/SKILL.md` (source of truth; mirrors regenerate via the sync hook), and the refine-deck skill's zero-edge sub-check comment stays consistent with it.
  - [ ] EMPIRICAL: re-running the predicate sweep from Skill(refine-deck) Step 2 over the open meta-fix-tagged cards yields zero false positives under the updated contract (spot-check documented in log.md).
  - [ ] MECHANICAL: `uv run goc validate` passes and `python scripts/sync_plugin_assets.py --check` is green.
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
  carry zero body-wide literals yet are the same architectural class as
  the tagged-and-wired umbrellas
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

## Resolution shapes

1. **Widen the predicate** to match practice: fire on body-wide
   literal, the `summary:` field, or a non-empty edge to a
   `meta-fix`-tagged card. Cheapest; ratifies the status quo.
2. **Keep the strict window predicate** and re-tag: strip the tag from
   every card failing it, keeping it only on family heads whose bodies
   open with the family framing. Consistent but churns ~a dozen cards
   and weakens the `goc --tag meta-fix` family view.
3. **Split the tag**: `meta-fix` for umbrella/guard cards only,
   membership expressed purely by edges. Requires migration and a
   schema PR.

Option 1 is the least-churn fit for the observed deck; the DoD leaves
the pick to whoever pulls this card.

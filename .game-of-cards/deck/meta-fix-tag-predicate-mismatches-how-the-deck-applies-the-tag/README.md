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

Empirical verification: all 45 open `meta-fix`-tagged cards pass the
widened predicate (37 of them fail the old strict window test); zero
false positives. Details in `log.md`.

---
title: surface-html-artifact-pattern-in-deck-views
summary: |
  GoC already supports sibling-file artifacts (`*.html`, `*.svg`, `*.png`)
  next to a card's README — see `Skill(create-card)` Step 7 and
  `Skill(card-schema)` lines 35-45. The pattern is documented but
  invisible from the daily verbs (`goc`, `goc show`, scan-deck), so it
  remains under-used. Surface it where users already look.
status: open
stage: null
contribution: low
created: 2026-05-10
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [ ] decision recorded below for which surface(s) carry the hint
  - [ ] chosen surfaces show artifact filenames or a one-line nudge
  - [ ] hint is concise (<= 1 line per card) — no UI clutter
  - [ ] `goc validate` still passes
  - [ ] `Skill(card-schema)` "Card Directory Layout" section unchanged
        (it already documents the pattern; this card is about discovery,
        not redocumentation)
---

# surface-html-artifact-pattern-in-deck-views

## What's missing

The artifact pattern (sibling `comparison-matrix.html`, `state-diagram.svg`,
`decision-form.html`, etc.) is fully documented and a previous card
(`card-skills-document-html-as-sibling-artifact-pattern`, done) landed
the docs. But none of the daily verbs hint that this option exists:

- `goc` queue view shows only title / status / contribution / value /
  gate / created / tags / DoD — no signal that a card carries rich
  artifacts.
- `goc show <title>` prints frontmatter and body but does not list
  sibling files.
- `Skill(scan-deck)` and `Skill(standup)` likewise are blind to
  artifacts.

So an agent or human filing a new card has no in-context reminder that
artifact files are available, even though they would benefit several
cards in the current deck (e.g., decision matrices that today render as
markdown tables).

## Why it matters

This is a "feature exists but nobody knows" defect — a documentation
discoverability gap, not a missing feature. The cost of a one-line nudge
in the right surface is tiny; the upside is broader use of a pattern
that already shipped.

## Decision required

Multiple surfaces could carry the hint; pick one to land first.

### Option A — list sibling files in `goc show <title>`

After printing frontmatter and body, append a `## Artifacts` section
listing any `*.html`, `*.svg`, `*.png`, `*.pdf` siblings. Zero output
when none exist.

- **Pro**: zero cost when no artifacts; only adds noise where it helps.
- **Con**: only triggers on explicit `show`. Casual `goc` queue users
  never see it.

### Option B — column or marker in queue / board view

Add a small `📎` or `[A]` marker in the rendered table when a card has
sibling artifacts. Costs one line per card to scan a directory.

- **Pro**: visible at a glance.
- **Con**: per-card filesystem stat on every render; emoji/ASCII
  styling churn.

### Option C — hint emitted by `Skill(create-card)` for decision-class cards

When the card's gate is `decision` or `session`, the skill body adds a
prompt: "Consider attaching a `decision-form.html` if the alternatives
benefit from side-by-side comparison."

- **Pro**: hint reaches the author at the moment of authoring.
- **Con**: skill-body change only — won't help anyone editing an
  already-filed card.

### Option D — combination

Option A + Option C: queue view stays clean, but both `show` and
`create-card` surface the pattern.

**Recommendation**: Option D. Queue view should stay information-dense
without ornamental columns; surfacing in `show` and at filing time
catches the two moments the pattern is most actionable.

## Notes

- Existing artifacts on disk: a quick scan would confirm whether
  current cards already use the pattern, which could inform the hint
  wording.
- Avoid adding a frontmatter field — sibling files are deliberately
  not parsed by the engine, and that property must be preserved.

---
title: surface-html-artifact-pattern-in-deck-views
summary: |-
  GoC already supports sibling-file artifacts (`*.html`, `*.svg`, `*.png`)
  next to a card's README — see `Skill(create-card)` Step 7 and
  `Skill(card-schema)` lines 35-45. The pattern is documented but
  invisible from the daily verbs (`goc`, `goc show`, scan-deck), so it
  remains under-used. Surface it where users already look.
status: active
stage: null
contribution: low
created: 2026-05-10
closed_at: null
human_gate: none
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
worker: {who: "claude[bot]", where: main}
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

## Decision

*Resolved 2026-05-10:* List sibling artifacts in 'goc show' as a ## Artifacts section (Option A) AND add a hint to the create-card skill body for decision/session cards (Option C); skip queue/board view markers.

*Reasoning:* the queue view stays clean while the two most actionable moments (filing and reading) carry the cue.
## Notes

- Existing artifacts on disk: a quick scan would confirm whether
  current cards already use the pattern, which could inform the hint
  wording.
- Avoid adding a frontmatter field — sibling files are deliberately
  not parsed by the engine, and that property must be preserved.

---
title: readme-starter-card-and-doc-polish-session
summary: "Run a human-guided documentation polish session covering the README's starter-card claim, install behavior, version/status wording, and first-run clarity."
status: open
stage: null
contribution: low
created: 2026-05-04
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [documentation, story]
definition_of_done: |
  - [ ] Decide whether `goc install` should create a starter card or whether the README should stop promising one
  - [ ] Review README first-run commands against actual CLI behavior from a fresh temporary repo
  - [ ] Fix stale release/status wording, including any `0.0.1` references that are live guidance rather than archival notes
  - [ ] Tighten the "what you get" list so it distinguishes CLI behavior, Claude skills, AGENTS.md guidance, and project-local hooks
  - [ ] Run a fresh install smoke test and record the exact commands/output in the card log
  - [ ] `goc validate` passes after README/doc edits
---

# readme-starter-card-and-doc-polish-session

## Decision required

This should be a session card because the product choice is not purely
mechanical: either `goc install` should really create a starter card, or
the README should stop saying it does. The right answer depends on the
desired first-run experience.

## Session prompt

Walk through the first-run README as a new user. Decide whether the
installer should create a demo card, then update the README and any
nearby guidance so the documented path matches the actual product.

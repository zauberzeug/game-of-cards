---
title: drop-prepare-commit-from-shipped-skills
summary: "Remove hard-coded `Skill(prepare-commit)` references from shipped GoC skills and leave project-specific commit workflows to hooks."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: []
advanced_by: []
tags: [infra, documentation]
definition_of_done: |
  - [x] Shipped GoC skill templates no longer reference `Skill(prepare-commit)` as a required or available skill
  - [x] Dogfood `.claude/skills/` copies match the template changes
  - [x] `finish-card` describes closure as a GoC close plus project hook / normal runtime commit behavior, with custom commit helpers left to consuming-repo hooks
  - [x] Related skills (`create-card`, `extend-deck`, `improve-deck`, `deck`, `advance-card`) no longer point at `prepare-commit`
  - [x] Sibling `../phasor-agents` finish-card skill is inspected and any necessary project-local fix is applied or reported
  - [x] `goc validate` passes after the cleanup
---

# drop-prepare-commit-from-shipped-skills

## Why

`prepare-commit` was a project-local Claude skill in the source repo that
GoC was extracted from. The public GoC install ships 11 skills and does
not ship `prepare-commit`, so the generic templates should not treat it
as part of the methodology.

## Scope

Replace hard-coded `Skill(prepare-commit)` references with generic
commit guidance. If a consuming repo wants a custom commit helper, it
belongs in `.game-of-cards/hooks/finish-card.md` or another
project-local hook, not in GoC's shipped skill surface.

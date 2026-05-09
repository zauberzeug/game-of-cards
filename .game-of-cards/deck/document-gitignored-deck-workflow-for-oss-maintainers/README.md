---
title: document-gitignored-deck-workflow-for-oss-maintainers
summary: "OSS-library maintainers face a tension that the deck-location decision (`evaluate-deck-as-separate-repo-or-submodule`) does not fully resolve: same-repo + checked-in pollutes PR diffs with card-state churn; same-repo + gitignored loses collaborative visibility. The recorded decision allows gitignore but does not guide the user through it. Document a concrete OSS-friendly recipe in PERSONAS.md (or a section of `DECK_LOCATION.md`) so a maintainer reading the docs can adopt the gitignore path with eyes open."
status: open
stage: null
contribution: low
created: 2026-05-09
closed_at: null
human_gate: none
advances:
  - evaluate-deck-as-separate-repo-or-submodule
  - support-external-game-of-cards-state-location
advanced_by: []
tags: [story, documentation]
definition_of_done: |
  - [ ] PERSONAS.md (classical-development team section) or DECK_LOCATION.md gains a concrete recipe for the gitignore path: which line to add to `.gitignore`, what `goc install` does when the deck is gitignored, what stops working (multi-machine sync, collaborator visibility), what still works (solo personal task state).
  - [ ] Trade-off explicit: solo-OSS-maintainer use case is served; multi-maintainer OSS use case is NOT served by this path — those maintainers should wait for `support-external-game-of-cards-state-location` to finish or for `explore-saas-deck-hosting-with-optional-tracker-sync` to ship.
  - [ ] Cross-link from the new doc back to `support-external-game-of-cards-state-location` (the active epic that recorded the gitignore decision).
  - [ ] `uv run goc validate` passes
---

# Document the gitignored-deck workflow for OSS maintainers

## Why

The decision recorded on `evaluate-deck-as-separate-repo-or-submodule` is that GoC ships only the same-repo configuration. The decision recorded on `support-external-game-of-cards-state-location` allows users to gitignore `.game-of-cards/` if they want.

OSS maintainers reading either decision today are left to figure the recipe out themselves. The DoD on the evaluate card flagged the need to surface this concern as a follow-up so it is not lost.

## What "good" looks like

A maintainer of an OSS library who reads PERSONAS.md (or follows the link from there to DECK_LOCATION.md) finds:

1. The gitignore line to add.
2. A clear statement of what stops working when the deck is gitignored (collaborators don't see your cards; multi-machine setups stop converging; CI-scheduled `pull-card` cannot operate on the deck unless something else publishes it).
3. A clear statement of what still works (solo task state for the maintainer; agent context across sessions on one machine; the local `goc` queue and Definition-of-Done enforcement).
4. A pointer to the active epic that may eventually offer a better path.

## Out of scope

- Implementing a sibling-repo or submodule discovery mechanism — that is the rejected direction from the evaluate card.
- Implementing the SaaS path — that is its own epic.
- Changing the gitignore default — the decision is to leave it checked-in by default and make gitignore an opt-in.

## Cross-references

- `evaluate-deck-as-separate-repo-or-submodule` (the card whose closure surfaced this follow-up)
- `support-external-game-of-cards-state-location` (active epic; recorded the gitignore-allowed decision)
- `explore-saas-deck-hosting-with-optional-tracker-sync` (the eventual better path for multi-maintainer OSS)

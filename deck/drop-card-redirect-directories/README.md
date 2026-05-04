---
title: drop-card-redirect-directories
summary: "Remove GoC's REDIRECT.md card-directory behavior: `goc move` should leave only the renamed card, validation should catch stale title references directly, and existing redirect-only directories should be deleted so decks do not accumulate dead weight."
status: active
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: [ship-game-of-cards-as-cross-agent-cli]
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] `goc move <old> <new>` no longer recreates `<old>/REDIRECT.md` after the rename; the old card directory is absent after a successful move
  - [ ] `load_all_cards` / board rendering no longer need redirect-only directory special cases
  - [ ] `goc validate` fails when `deck/` contains a redirect-only card directory or any other stale card-name directory without a valid `README.md`
  - [ ] `goc validate` continues to catch stale references in `advances` / `advanced_by` after a move, so redirects are not needed as a compatibility layer
  - [ ] Existing `deck/goc-*/REDIRECT.md` directories in this repo are removed and no equivalent redirect directories remain
  - [ ] Tests or smoke coverage exercise moving a card, validating a stale relation, and rejecting a redirect-only directory
  - [ ] Docs/help text for `goc move` no longer promises a redirect stub
---

# Drop Card Redirect Directories

## Why

The current `goc move` flow preserves old card names by creating
`deck/<old-title>/REDIRECT.md`. That keeps historical paths alive, but it makes
the deck heavier every time names are cleaned up. For GoC usage, the cleaner
contract is: the deck contains live cards only, and validation catches stale
references to old titles.

## What

Change move/validation semantics so card renames are real renames:

1. Move the directory to the new title.
2. Rewrite the card's frontmatter title and known relation fields.
3. Do not create a redirect directory.
4. Let `goc validate` fail on stale relation references or stale filesystem
   entries instead of silently ignoring redirect-only directories.

As part of this cleanup, remove the existing redirect-only directories from
this repository's deck so installed and dogfooded GoC decks do not accumulate
dead weight.

## Pointers

- Current loader special case: `goc/engine.py` skips directories containing
  `REDIRECT.md` without `README.md`.
- Current move behavior: `goc move` recreates the old directory and writes
  `REDIRECT.md` after `git mv`.

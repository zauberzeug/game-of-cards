---
title: move-deck-into-game-of-cards-directory
summary: "Move the canonical deck location from root `deck/` to `.game-of-cards/deck` so GoC-owned project state lives under one runtime-neutral directory. Preserve compatibility or provide a migration path for existing decks, and keep config under `.game-of-cards` with one documented filename."
status: active
stage: null
contribution: high
created: 2026-05-05
closed_at: null
human_gate: none
advances: [support-external-game-of-cards-state-location]
advanced_by: []
tags: [story, infra, api-contract]
definition_of_done: |
  - [ ] CLI discovers cards from `.game-of-cards/deck` as the canonical deck path
  - [ ] Existing root `deck/` installs either keep working through compatibility lookup or migrate through an explicit command/path
  - [ ] `.goc-version` and other deck metadata move under `.game-of-cards/deck`
  - [ ] `.game-of-cards/config.yaml` remains the documented config path, or an intentional `config.yml` alias/rename is implemented consistently
  - [ ] `goc install` scaffolds new repos with `.game-of-cards/deck`
  - [ ] `goc validate`, `goc new`, `goc status`, `goc done`, `goc advance`, `goc move`, and board/queue views work against the new path
  - [ ] Tests cover new-path decks, old root decks, and mixed/conflicting deck locations
  - [ ] This repo is migrated or has an explicit compatibility note
  - [ ] `uv run goc validate` passes
---

# Move the deck into `.game-of-cards`

## Why

GoC-owned project state should have one home. The clarified direction is to stop treating root `deck/` as the canonical project artifact and move the deck under `.game-of-cards`, beside the runtime-neutral config and hook stubs.

## Decision

Use `.game-of-cards/deck` as the canonical deck location. Keep the existing `.game-of-cards/config.yaml` spelling unless a later decision intentionally renames or aliases it.

## Notes

This card is the concrete filesystem migration under the parent `support-external-game-of-cards-state-location`. It should be coordinated with optional skill/hook installation, because moving state does not by itself solve checked-in runtime affordances.

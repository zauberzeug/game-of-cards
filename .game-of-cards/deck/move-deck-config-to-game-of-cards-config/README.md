---
title: move-deck-config-to-game-of-cards-config
summary: "Move GoC closure/configuration state out of Claude-specific `.claude/deck-config.yaml` and into a runtime-neutral `.game-of-cards/config.yaml`."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: [configurable-auto-commit]
advanced_by: []
tags: [infra, api-contract]
definition_of_done: |
  - [x] Add `.game-of-cards/config.yaml` to the shipped template set with documented sections for closure attestation and workflow options
  - [x] Update `goc attest` / config loading to read `.game-of-cards/config.yaml` first, with a clear migration path for existing `.claude/deck-config.yaml`
  - [x] Remove live references to `.claude/deck-config.yaml` from shipped skills, card-schema guidance, and engine comments
  - [x] Update `goc install` / `goc upgrade` so new installs get runtime-neutral config and existing installs are migrated without clobbering custom checks
  - [x] Update phasor-agents migration notes or hooks so its project-specific closure checks can live under `.game-of-cards/config.yaml`
  - [x] `goc validate` and a focused `goc attest` smoke test pass against the new config location
---

# move-deck-config-to-game-of-cards-config

## Why

`deck-config.yaml` is GoC methodology state, not Claude Code state.
Keeping it under `.claude/` makes closure attestation look
runtime-specific and blocks the AGENTS.md story for Codex, Cursor,
OpenCode, Copilot, and shell users.

## Scope

Create one general `.game-of-cards/config.yaml` home for configuration
currently split between engine defaults, skill prose, and
`.claude/deck-config.yaml`. This is the neutral substrate for the
separate auto-commit configurability card.

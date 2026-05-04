---
title: configurable-auto-commit
summary: "Make GoC's state-change auto-commit behavior explicit and configurable through install-time defaults plus `.game-of-cards/config.yaml`."
status: active
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: [move-deck-config-to-game-of-cards-config]
tags: [infra, api-contract]
definition_of_done: |
  - [ ] Add a shipped `.game-of-cards/config.yaml` template with an `auto_commit` setting and documented default
  - [ ] Extend `goc install` / `goc upgrade` so the config is created or migrated without clobbering consuming-repo custom values
  - [ ] Teach state-mutating commands (`status`, `advance`, `unadvance`, `decide`, and any future close behavior if applicable) to respect the config while preserving explicit CLI overrides
  - [ ] Update AGENTS/CLAUDE skill guidance so auto-commit is described as a configured policy, not a hard-coded invariant
  - [ ] Add focused coverage or smoke commands proving both enabled and disabled modes
  - [ ] `goc validate` passes after the config changes
---

# configurable-auto-commit

## Why

The current engine auto-commits some deck state mutations and leaves
closure bundled with the work diff. That can be useful for autonomous
multi-branch work, but it is a workflow policy, not a universal truth.
Consuming repos need a visible switch for it.

## Scope

Introduce a project-local config file under `.game-of-cards/config.yaml`
and let install-time scaffolding choose the default. The command-line
surface should still allow an explicit per-command override.

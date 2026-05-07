---
title: make-skill-and-hook-installation-optional
summary: "Change install/upgrade so generated agent skills and hooks are optional runtime affordances, not mandatory checked-in files in every consuming repo. CLI-only GoC should be usable with `.game-of-cards` project state, while users can opt into repo-local shims or plugin-provided skills/hooks."
status: done
stage: null
contribution: high
created: 2026-05-05
closed_at: 2026-05-05
human_gate: none
advances:
  - support-external-game-of-cards-state-location
advanced_by: []
tags: [story, infra, api-contract]
definition_of_done: |
  - [x] `goc install` exposes an explicit mode that installs project state without generated agent skills/hooks
  - [x] Existing Claude/Codex harness installation remains available as an opt-in compatibility mode
  - [x] Install/upgrade dry-run output clearly separates project state, guidance files, and runtime affordances
  - [x] Generated AGENTS/CLAUDE/Codex guidance no longer implies skills/hooks must be checked into the repo
  - [x] Hook registration is skipped cleanly when hooks are not requested
  - [x] Tests cover CLI-only install, Claude/Codex opt-in install, upgrade from older installs, and dry-run output
  - [x] Docs explain when to use CLI-only, repo-local harness, or plugin-provided runtime files
  - [x] `uv run goc validate` passes
---

# Make skill and hook installation optional

## Why

The repo should not have to check in generated skills and hooks just to use GoC. Those files are runtime affordances for specific agents, while the methodology state lives in `.game-of-cards` and the engine lives in the `goc` CLI.

## Shape

Separate install output into three categories:

- Project state: `.game-of-cards/deck`, `.game-of-cards/config.yaml`, and project-local GoC content.
- Repo guidance: minimal AGENTS/CLAUDE/Codex instructions if requested.
- Runtime affordances: skills, hooks, commands, or plugin files for a specific agent.

The default can change only if docs and migration behavior make the repo-footprint contract explicit.

---
title: provide-claude-code-plugin-for-skills-and-hooks
summary: "Make this repository provide a Claude Code plugin that supplies Game of Cards skills and hooks, so consuming repos do not need to check generated `.claude/skills` and hook files into source control. The plugin should delegate durable project state to `.game-of-cards` and the `goc` CLI."
status: open
stage: null
contribution: high
created: 2026-05-05
closed_at: null
human_gate: session
advances: [support-external-game-of-cards-state-location, publish-game-of-cards-agent-plugins]
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] Claude Code plugin packaging/discovery format is confirmed and recorded
  - [ ] Plugin manifest/source lives in this repo and includes GoC skills and hook assets
  - [ ] Plugin-provided skills shell to the installed `goc` CLI and do not carry independent methodology state
  - [ ] Plugin hook behavior can be enabled without copying hook scripts into the consuming repo as checked-in files
  - [ ] Plugin works with `.game-of-cards/deck` and optional skill/hook install modes
  - [ ] Local plugin smoke test confirms Claude Code can discover skills/hooks through the plugin path
  - [ ] Docs explain plugin install/use and compatibility with repo-local harness mode
  - [ ] `uv run goc validate` passes
---

# Provide a Claude Code plugin for skills and hooks

## Why

Claude Code is the original GoC runtime, but repo-local generated `.claude/skills` and hook files should not be the only distribution path. A plugin lets this repository provide the runtime affordances while consuming repositories keep only durable project state and minimal guidance.

## Session required

This needs a packaging/session pass because plugin format, hook registration, local development workflow, and publication path are part of the product contract.

---
title: publish-game-of-cards-agent-plugins
summary: "Publish the Game of Cards agent plugins once Claude Code, Codex, and later OpenClaw plugin packages exist. This is release/distribution work distinct from implementing any one plugin."
status: open
stage: null
contribution: medium
created: 2026-05-05
closed_at: null
human_gate: session
advances: [support-external-game-of-cards-state-location]
advanced_by: [provide-claude-code-plugin-for-skills-and-hooks, provide-codex-plugin-for-skills-and-hooks, provide-openclaw-plugin-for-skills-and-hooks]
tags: [story, infra]
definition_of_done: |
  - [ ] Publication targets accepted for each plugin runtime
  - [ ] Versioning policy documented for plugin packages relative to the `game-of-cards` PyPI package
  - [ ] Release workflow or manual release checklist exists for each plugin
  - [ ] Published plugin artifacts can be installed by a fresh consumer environment
  - [ ] Docs link users to the correct plugin install path and explain compatibility with CLI-only/repo-local modes
  - [ ] Smoke tests or release verification steps cover published artifacts
  - [ ] `uv run goc validate` passes
---

# Publish Game of Cards agent plugins

## Why

Implementing plugin files in the repo is not the same as making them available to users. Plugin publication needs its own release discipline: artifact names, versioning, registry/marketplace targets, compatibility notes, and smoke tests.

## Scope

This card tracks publishing, not plugin implementation. It depends on the runtime-specific plugin cards.

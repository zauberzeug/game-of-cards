---
title: publish-game-of-cards-agent-plugins
summary: "Publish the Game of Cards agent plugins once Claude Code, Codex, and later OpenClaw plugin packages exist. This is release/distribution work distinct from implementing any one plugin."
status: superseded
stage: null
contribution: medium
created: 2026-05-05
closed_at: null
human_gate: none
advances: []
advanced_by: []
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

## Superseded 2026-05-06

Bundling all-runtime publication into one card meant Claude release was gated on Codex + OpenClaw publication, even though the Claude plugin payload is already done. There is also a likely fourth target (Cursor) that doesn't fit a fixed-runtime list. Split into per-runtime publish cards so each can ship independently:

- `publish-claude-code-plugin`
- `publish-codex-plugin`
- `publish-openclaw-plugin`

Future targets (e.g. `publish-cursor-plugin`) get their own cards as those runtimes' plugin formats settle.


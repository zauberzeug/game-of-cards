---
title: provide-claude-code-plugin-for-skills-and-hooks
summary: "Make this repository provide a Claude Code plugin that supplies Game of Cards skills and hooks, so consuming repos do not need to check generated `.claude/skills` and hook files into source control. The plugin should delegate durable project state to `.game-of-cards` and the `goc` CLI."
status: done
stage: null
contribution: high
created: 2026-05-05
closed_at: 2026-05-05
human_gate: none
advances: [support-external-game-of-cards-state-location, publish-game-of-cards-agent-plugins]
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] Claude Code plugin packaging/discovery format is confirmed and recorded
  - [x] Plugin manifest/source lives in this repo and includes GoC skills and hook assets
  - [x] Plugin-provided skills shell to the installed `goc` CLI and do not carry independent methodology state
  - [x] Plugin hook behavior can be enabled without copying hook scripts into the consuming repo as checked-in files
  - [x] Plugin works with `.game-of-cards/deck` and optional skill/hook install modes
  - [x] Local plugin smoke test confirms Claude Code can discover skills/hooks through the plugin path
  - [x] Docs explain plugin install/use and compatibility with repo-local harness mode
  - [x] `uv run goc validate` passes
---

# Provide a Claude Code plugin for skills and hooks

## Why

Claude Code is the original GoC runtime, but repo-local generated `.claude/skills` and hook files should not be the only distribution path. A plugin lets this repository provide the runtime affordances while consuming repositories keep only durable project state and minimal guidance.

## Session required

This needs a packaging/session pass because plugin format, hook registration, local development workflow, and publication path are part of the product contract.

## Decision

*Resolved 2026-05-05:* (1) single plugin 'game-of-cards' covering all skills + hooks; (2) plugin source lives at top-level claude-plugin/ sibling to goc/, with skills/ and hooks/ as symlinks into goc/templates/ (single source of truth); (3) plugin skills shell to goc CLI and document pip/uv install as prerequisite, with a minimum goc version pin; (4) hook scripts referenced via ${CLAUDE_PLUGIN_ROOT}/hooks/... so consumer repos check in zero hook files; (5) plugin wins over repo-local .claude/skills when both exist; provide goc uninstall --runtime claude to clean up old copies (no auto-migration); (6) two-step distribution: local 'claude plugin install /path' for dev + marketplace publication tracked under publish-game-of-cards-agent-plugins; (7) no CI behavioral smoke test — symlinks into goc/templates/ make structural drift impossible, and behavioral verification is a manual local-install checklist; (8) plugin version locked to goc package version, released together by tag

*Reasoning:* Symlinks collapse the third-copy problem and obviate the smoke test in one move — the templates the wheel ships ARE the plugin payload, so any divergence would be a filesystem error, not a logic bug. Lockstep versioning + single plugin + CLI-as-prereq match the existing dogfood model where goc is the engine and runtime affordances wrap it. Explicit uninstall over auto-migration keeps the coexistence story debuggable.

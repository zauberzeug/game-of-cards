---
title: provide-codex-plugin-for-skills-and-hooks
summary: "Provide a Codex plugin or equivalent Codex runtime package for Game of Cards skills and hooks, matching the Claude plugin direction where the runtime supports it. The goal is to avoid checked-in `.codex/skills` copies while preserving the same `goc`-backed workflow."
status: open
stage: null
contribution: high
created: 2026-05-05
closed_at: null
human_gate: session
advances:
  - support-external-game-of-cards-state-location
  - publish-codex-plugin
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] Codex plugin/runtime extension format is confirmed and recorded
  - [ ] Plugin or equivalent package supplies GoC skills/instructions without requiring checked-in `.codex/skills`
  - [ ] Plugin-provided skills delegate to the installed `goc` CLI and `.game-of-cards` state
  - [ ] Hook or prompt-routing support is implemented where Codex supports it, or explicitly documented as unsupported
  - [ ] Behavior stays consistent with Claude plugin and optional repo-local harness modes
  - [ ] Local smoke test confirms Codex can discover/use the GoC runtime affordance
  - [ ] Docs explain install/use and limitations
  - [ ] `uv run goc validate` passes
---

# Provide a Codex plugin for skills and hooks

## Why

Codex already has a first-class harness card, but the new direction is plugin-provided runtime affordances instead of checked-in generated skills. This card tracks the Codex side of that split.

## Session required

This needs a session because Codex plugin capabilities and hook equivalents must be verified before implementation. If Codex cannot provide a true plugin path, the accepted fallback should be documented explicitly.

---
title: provide-openclaw-plugin-for-skills-and-hooks
summary: "Replace the blocked OpenClaw harness direction with a later OpenClaw plugin/runtime package for Game of Cards skills and hooks. This supersedes `install-openclaw-harness` and should wait until the Claude/Codex plugin pattern is clear or an OpenClaw consumer appears."
status: open
stage: null
contribution: medium
created: 2026-05-05
closed_at: null
human_gate: session
advances:
  - support-external-game-of-cards-state-location
  - publish-openclaw-plugin
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] `install-openclaw-harness` is marked superseded with a log entry pointing here
  - [ ] OpenClaw plugin/runtime extension format is confirmed from current upstream docs or source before implementation
  - [ ] Plugin supplies GoC instructions/skills/hooks through OpenClaw's native mechanism where possible
  - [ ] Plugin delegates durable state to `.game-of-cards` and the `goc` CLI
  - [ ] Docs list OpenClaw plugin support separately from repo-local harness installation
  - [ ] Smoke test confirms OpenClaw can discover/use the plugin in a fresh repo
  - [ ] `uv run goc validate` passes
---

# Provide an OpenClaw plugin for skills and hooks

## Why

The previous OpenClaw work was framed as another `goc install --agents openclaw` repo-local harness. The clarified direction is plugin-first: Claude Code and Codex plugins first, then OpenClaw later. This card replaces the blocked harness card.

## Timing

This is intentionally later-stage work. It should not be pulled until the plugin shape is proven for at least one primary runtime or a concrete OpenClaw consuming repo needs it.

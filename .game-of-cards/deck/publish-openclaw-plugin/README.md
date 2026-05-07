---
title: publish-openclaw-plugin
summary: "Publish the Game of Cards OpenClaw plugin/runtime package once `provide-openclaw-plugin-for-skills-and-hooks` lands. Distribution-only work scoped to OpenClaw."
status: open
stage: null
contribution: medium
created: 2026-05-06
closed_at: null
human_gate: session
advances:
  - support-external-game-of-cards-state-location
advanced_by:
  - provide-openclaw-plugin-for-skills-and-hooks
tags: [story, infra]
definition_of_done: |
  - [ ] OpenClaw publication target chosen and recorded
  - [ ] Versioning policy documented relative to the `game-of-cards` PyPI package
  - [ ] Release workflow or manual checklist exists for OpenClaw artifacts
  - [ ] Published artifact installable by a fresh consumer environment with `goc` on PATH
  - [ ] Docs link users to the OpenClaw install path
  - [ ] Smoke test or release-verification step covers OpenClaw artifacts
  - [ ] `uv run goc validate` passes
---

# Publish the OpenClaw plugin

## Why

OpenClaw plugin implementation is tracked under `provide-openclaw-plugin-for-skills-and-hooks`. Once that card lands, this card owns turning the artifact into something users can install.

## Scope

OpenClaw-only. Split out from the previous bundled card `publish-game-of-cards-agent-plugins` so each runtime publishes on its own timeline.

## Depends on

- `provide-openclaw-plugin-for-skills-and-hooks` (implementation, currently blocked on the OpenClaw direction itself)

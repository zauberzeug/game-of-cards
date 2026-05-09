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
  - [ ] Plugin published on ClawHub (<https://clawhub.ai>) such that consumers can install via `openclaw skills install <id>`; chosen package id recorded in this card's log
  - [ ] If an npm-only mirror is also chosen, npm package name recorded in this card's log
  - [ ] Versioning policy documented relative to the `game-of-cards` PyPI package
  - [ ] Release workflow or manual checklist exists for OpenClaw artifacts
  - [ ] Published artifact installable by a fresh consumer environment with `goc` on PATH
  - [ ] Docs link users to the OpenClaw install path (ClawHub link primary; npm command secondary if applicable)
  - [ ] Smoke test or release-verification step covers OpenClaw artifacts
  - [ ] `uv run goc validate` passes
---

# Publish the OpenClaw plugin

## What is OpenClaw

OpenClaw is an open-source personal AI assistant (<https://github.com/openclaw/openclaw>, <https://openclaw.ai>) — Node-based, npm-distributed (`npm install -g openclaw@latest`), with a public skills registry called **ClawHub** at <https://clawhub.ai>. Skills are `SKILL.md` directories installed via `openclaw skills install`. **Distinct from OpenCode (sst/opencode).** Full identity anchor with verified upstream sources lives on `provide-openclaw-plugin-for-skills-and-hooks`.

## Why

OpenClaw plugin implementation is tracked under `provide-openclaw-plugin-for-skills-and-hooks`. Once that card lands, this card owns turning the artifact into something users can install.

## Scope

OpenClaw-only. Split out from the previous bundled card `publish-game-of-cards-agent-plugins` so each runtime publishes on its own timeline. Likely targets:

- Listing on the ClawHub registry so consumers can `openclaw skills install game-of-cards` (or whatever the chosen package id is)
- Optionally an npm package mirror so consumers without ClawHub can install directly via `npm`

The final channel mix is set by the discovery output recorded on `provide-openclaw-plugin-for-skills-and-hooks` and locked in here before this card is pulled.

## Depends on

- `provide-openclaw-plugin-for-skills-and-hooks` (implementation, currently session-gated pending the discovery sitting)

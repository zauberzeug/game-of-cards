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
  - add-openclaw-install-section-to-llms-txt
tags: [story, infra]
definition_of_done: |
  - [ ] Plugin published on ClawHub (<https://clawhub.ai>) such that consumers can install via `openclaw skills install <id>`; chosen package id recorded in this card's log
  - [ ] Plugin published as the npm package `game-of-cards` (name verified available on the npm registry 2026-05-09); both channels live
  - [ ] Versioning policy documented relative to the `game-of-cards` PyPI package (single source of truth — npm and ClawHub track PyPI version)
  - [ ] Release workflow or manual checklist exists for OpenClaw artifacts (covers ClawHub + npm)
  - [ ] Published artifact installable by a fresh consumer environment with `python3` (3.10+) on PATH (no `uv` and no `pipx` step required; the plugin vendors the goc engine and uses a `bin/goc` python3 wrapper, parallel to the Claude plugin after `plugin-wrapper-drops-uv`)
  - [ ] Docs link users to both install paths (ClawHub primary; npm as alternative)
  - [ ] Smoke test or release-verification step covers both channels
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# Publish the OpenClaw plugin

## What is OpenClaw

OpenClaw is an open-source personal AI assistant (<https://github.com/openclaw/openclaw>, <https://openclaw.ai>) — Node-based, npm-distributed (`npm install -g openclaw@latest`), with a public skills registry called **ClawHub** at <https://clawhub.ai>. Skills are `SKILL.md` directories installed via `openclaw skills install`. **Distinct from OpenCode (sst/opencode).** Full identity anchor with verified upstream sources lives on `provide-openclaw-plugin-for-skills-and-hooks`.

## Why

OpenClaw plugin implementation is tracked under `provide-openclaw-plugin-for-skills-and-hooks`. Once that card lands, this card owns turning the artifact into something users can install.

## Scope

OpenClaw-only. Split out from the previous bundled card `publish-game-of-cards-agent-plugins` so each runtime publishes on its own timeline. Distribution decided 2026-05-09 on `provide-openclaw-plugin-for-skills-and-hooks`:

- ClawHub registry listing so consumers can `openclaw skills install game-of-cards`
- npm package `game-of-cards` (name verified available on the npm registry 2026-05-09; `goc` is squatted with a placeholder, so the longer name is the clean choice and also matches the PyPI name)

Both channels publish from the same artifact; npm doubles as a name-claiming step on the registry.

## Depends on

- `provide-openclaw-plugin-for-skills-and-hooks` (implementation; gate now `none`, pullable when its turn comes)

## Decision required (2026-05-09)

Blocked by `provide-openclaw-plugin-for-skills-and-hooks` which is parked at gate:session pending human decisions about the wrapper pattern and external publishing accounts.

This card requires: (1) the parent card to land, (2) ClawHub and npm publishing credentials available to the executor, (3) human-verified smoke test. All three items require human action. Raising gate to session until the parent is resolved.

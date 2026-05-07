---
title: publish-codex-plugin
summary: "Publish the Game of Cards Codex plugin/runtime package once `provide-codex-plugin-for-skills-and-hooks` lands. Distribution-only work scoped to the Codex runtime."
status: open
stage: null
contribution: medium
created: 2026-05-06
closed_at: null
human_gate: session
advances:
  - support-external-game-of-cards-state-location
advanced_by:
  - provide-codex-plugin-for-skills-and-hooks
tags: [story, infra]
definition_of_done: |
  - [ ] Codex publication target chosen and recorded (Codex marketplace if/when it exists, npm package, or direct-install URL)
  - [ ] Versioning policy documented relative to the `game-of-cards` PyPI package
  - [ ] Release workflow or manual checklist exists for Codex artifacts
  - [ ] Published artifact installable by a fresh consumer environment with `goc` on PATH
  - [ ] Docs link users to the Codex install path
  - [ ] Smoke test or release-verification step covers Codex artifacts
  - [ ] `uv run goc validate` passes
---

# Publish the Codex plugin

## Why

Codex plugin implementation is tracked under `provide-codex-plugin-for-skills-and-hooks`. Once that card lands, the artifact still needs a distribution path; this card owns that distribution work for Codex specifically.

## Scope

Codex-only. Split out from the previous bundled card `publish-game-of-cards-agent-plugins` so Claude and OpenClaw publication don't gate each other.

## Depends on

- `provide-codex-plugin-for-skills-and-hooks` (implementation)
- The Codex runtime's plugin/extension format being settled (open question on that card)

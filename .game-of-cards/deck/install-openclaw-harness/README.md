---
title: install-openclaw-harness
summary: "Make OpenClaw a first-class `goc install` harness option, following its native project-guidance convention while sharing GoC's common harness metadata."
status: superseded
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] OpenClaw's current project-guidance file/path convention is verified from upstream docs or source before implementation and recorded in this card log
  - [ ] `goc install --agents openclaw` installs the shared GoC repo scaffold plus OpenClaw-native harness files, without writing Claude-only `.claude/skills/` or prompt-hook files unless `claude` is also selected
  - [ ] The OpenClaw harness content is generated from shared harness metadata wherever possible; only path/format glue is OpenClaw-specific
  - [ ] `goc install --dry-run --agents openclaw` reports the exact OpenClaw harness writes and shared writes
  - [ ] Documentation lists `openclaw` as a supported install target and shows the install command alongside `claude` and `codex`
  - [ ] Fresh-repo smoke test: install the OpenClaw harness, create a card, validate the deck, and confirm OpenClaw can discover the GoC instructions through its native convention
---

# Install OpenClaw Harness

## What is OpenClaw

OpenClaw is an open-source personal AI assistant (<https://github.com/openclaw/openclaw>, <https://openclaw.ai>) — Node-based, npm-distributed, with skills published on the ClawHub registry (<https://clawhub.ai>). **Not a typo for OpenCode (sst/opencode); they are unrelated products.** Full identity anchor lives on `provide-openclaw-plugin-for-skills-and-hooks`.

## Superseded

This card is replaced by [provide-openclaw-plugin-for-skills-and-hooks](../provide-openclaw-plugin-for-skills-and-hooks/).

The product direction changed from repo-local harness installation (`goc install --agents openclaw`) to plugin-provided runtime affordances. OpenClaw support should follow the plugin path after the Claude Code and Codex plugin shapes are proven, instead of adding another checked-in harness target.

## Why

OpenClaw should be an explicit install target rather than a generic AGENTS.md
side effect. Keeping it separate lets the implementation match OpenClaw's
native convention while still sharing the same GoC command vocabulary and
Definition-of-Done behavior.

## What

Deferred as of 2026-05-04. OpenCLAW installation is not needed in this repo, so
the harness should stay out of the current implementation queue until a concrete
downstream repo needs OpenCLAW-native GoC guidance.

If reopened, the first implementation step is still to confirm OpenCLAW's
current guidance-file convention, then add the smallest native shim that points
OpenCLAW at the shared GoC runtime.

## Cross-references

- Parent split card: `multi-agent-shim-which-agents-at-v1`
- Sibling harness cards: `install-claude-harness`, `install-codex-harness`

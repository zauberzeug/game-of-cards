---
title: install-openclaw-harness
summary: "Make OpenClaw a first-class `goc install` harness option, following its native project-guidance convention while sharing GoC's common harness metadata."
status: open
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: [multi-agent-shim-which-agents-at-v1]
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

## Why

OpenClaw should be an explicit install target rather than a generic AGENTS.md
side effect. Keeping it separate lets the implementation match OpenClaw's
native convention while still sharing the same GoC command vocabulary and
Definition-of-Done behavior.

## What

Add an OpenClaw harness target to the install selector. The first implementation
step is to confirm OpenClaw's current guidance-file convention, then add the
smallest native shim that points OpenClaw at the shared GoC runtime.

## Cross-references

- Parent split card: `multi-agent-shim-which-agents-at-v1`
- Sibling harness cards: `install-claude-harness`, `install-codex-harness`

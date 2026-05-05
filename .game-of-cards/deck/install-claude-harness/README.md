---
title: install-claude-harness
summary: "Make Claude Code a first-class `goc install` harness option, preserving the existing skills + hook experience behind an explicit installer selector."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: [multi-agent-shim-which-agents-at-v1]
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] `goc install --agents claude` installs the Claude Code harness explicitly: `.claude/skills/`, `.claude/hooks/user-prompt-submit-goc.py`, the Claude-specific `CLAUDE.md` block, and the shared GoC repo scaffold
  - [x] The no-flag install default is documented and tested; if the default remains Claude, it is behaviorally equivalent to `--agents claude`
  - [x] `goc install --dry-run --agents claude` lists only the Claude harness files plus shared deck/config/doc writes
  - [x] `goc upgrade` re-syncs the Claude harness without clobbering user-authored cards or unrelated non-Claude harness files
  - [x] README/support docs list `claude` as a supported install target and explain that the silent-runtime prompt hook is Claude-specific
  - [x] Fresh-repo smoke test: install the Claude harness, create a card, validate the deck, and confirm the installed Claude instructions reference the generated skill names correctly
---

# Install Claude Harness

## Why

The current installer grew out of the Claude Code path: it writes Claude skills,
the UserPromptSubmit hook, and a Claude-specific `CLAUDE.md` delta. That should
remain supported, but it should be one explicit harness choice rather than the
shape every runtime inherits.

## What

Keep the existing Claude experience intact behind an installer option matching
the multi-harness selector. This card owns the Claude-specific files and
behavior; Codex and OpenClaw get separate cards so their conventions can evolve
without being coupled to Claude's hook and skill model.

## Cross-references

- Parent split card: `multi-agent-shim-which-agents-at-v1`
- Sibling harness cards: `install-codex-harness`, `install-openclaw-harness`

---
title: install-codex-harness
summary: "Make OpenAI Codex a first-class `goc install` harness option with AGENTS.md-centered guidance and no Claude-only skill or hook assumptions."
status: active
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: [multi-agent-shim-which-agents-at-v1]
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] `goc install --agents codex` installs the shared GoC repo scaffold and Codex-usable guidance without writing Claude-only `.claude/skills/` or prompt-hook files unless `claude` is also selected
  - [ ] The installed `AGENTS.md` block is sufficient for Codex to run the GoC session-mode pipeline using CLI verbs (`goc new`, `goc status`, `goc done`, `goc validate`) and contains no `Skill(...)` notation
  - [ ] Any Codex-specific harness template path/content is generated from shared harness metadata rather than duplicating the full methodology text by hand
  - [ ] `goc install --dry-run --agents codex` reports the exact Codex harness writes and shared writes
  - [ ] Documentation lists `codex` as a supported install target, including the expected command examples for local development and installed-package use
  - [ ] Fresh-repo smoke test: install the Codex harness, remove any Claude-only files if present, create a card, validate the deck, and confirm the AGENTS guidance is the only required runtime briefing
---

# Install Codex Harness

## Why

Codex reads repo guidance through `AGENTS.md`, not Claude Code skills or hooks.
GoC should be directly usable from Codex sessions by installing the shared deck
scaffold plus guidance that tells Codex exactly how to drive the CLI.

## What

Add a Codex harness target to the install selector. The target should keep the
agent-facing surface small and explicit: Codex gets the deck workflow, command
examples, and Andon-cord behavior in `AGENTS.md`; it should not inherit Claude's
skill files or prompt hook as accidental dependencies.

## Cross-references

- Parent split card: `multi-agent-shim-which-agents-at-v1`
- Sibling harness cards: `install-claude-harness`, `install-openclaw-harness`

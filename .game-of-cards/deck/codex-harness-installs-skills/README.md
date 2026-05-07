---
title: codex-harness-installs-skills
summary: Make the Codex install target write GoC skill files so Codex can discover and invoke the workflow by skill name.
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [x] `goc install --agents codex --dry-run` lists Codex skill writes, not only `AGENTS.md`
  - [x] `goc install --codex` is accepted as a shorthand for the Codex harness
  - [x] Fresh Codex install writes the GoC skill tree under a Codex-readable skills location
  - [x] `goc upgrade --agents codex` refreshes the Codex skill tree
  - [x] Shipped GoC skill templates contain Codex-required `name` metadata
  - [x] README/docs describe Codex as installing skills, not just `AGENTS.md`
  - [x] `uv run goc validate` and focused installer smoke checks pass
---

# Codex Harness Installs Skills

## Why

The Codex harness currently installs deck/config state plus `AGENTS.md`.
That lets Codex follow the workflow manually, but it does not make GoC's
workflow skills available as Codex skills. The install target should expose
the same action surface that Claude gets, without writing Claude-only hooks.

## What

Install the shared GoC skill templates for the `codex` harness and make the
skill frontmatter satisfy Codex's `name` + `description` metadata contract.
Keep Claude's prompt hook scoped to the Claude harness.

---
title: load-claude-instructions-from-agents
summary: "Root `CLAUDE.md` contains the repo's main agent guidance while `AGENTS.md` only carries the GoC block. Move the shared guidance into `AGENTS.md` and reduce `CLAUDE.md` to a Claude Code import of `AGENTS.md`, matching the cross-runtime single-source pattern the user requested."
status: active
stage: null
contribution: medium
created: "2026-05-18T03:33:25Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [ ] `AGENTS.md` contains the previously Claude-only repo guidance that is relevant to all LLM agents, while preserving the existing repo-local `uv run goc ...` note and GoC marker block.
  - [ ] `CLAUDE.md` contains only an `@AGENTS.md` import (plus no duplicated repo guidance).
  - [ ] Self-referential wording in the moved guidance no longer claims the canonical guidance lives in `CLAUDE.md` where `AGENTS.md` is the new source of truth.
  - [ ] `uv run goc validate` passes.
worker: {who: Rodja Trappe, where: main}
---

# Load Claude instructions from AGENTS

## Summary

The root `CLAUDE.md` currently holds the detailed repo instructions:
common commands, release flow, code architecture, template ownership, and
plugin asset rules. The root `AGENTS.md` only contains a repo-local
`uv run goc ...` note plus the generated GoC methodology block.

The user requested the cross-runtime shape used by `nicegui.io`: shared
agent guidance lives in `AGENTS.md`, and `CLAUDE.md` simply imports it
with Claude Code's `@AGENTS.md` syntax.

## Location

- `CLAUDE.md`
- `AGENTS.md`

## Work

Move all repo-relevant, LLM-universal guidance from `CLAUDE.md` into
`AGENTS.md`. Keep the existing `AGENTS.md` GoC block and repo-local GoC
command note. Then replace `CLAUDE.md` with only:

```markdown
@AGENTS.md
```

While moving content, update self-references that point at `CLAUDE.md`
as the canonical source of repo guidance so they point at `AGENTS.md`
where appropriate. Claude-specific product names may stay when they
describe actual Claude Code plugin or workflow surfaces.

## Why It Matters

`AGENTS.md` is the cross-runtime instruction file for Codex and other
agent tools. Keeping most repo knowledge in `CLAUDE.md` hides it from
non-Claude agents and creates a misleading split between two root-level
instruction files. A one-line Claude import keeps Claude Code behavior
intact without duplicating or fragmenting the guidance.

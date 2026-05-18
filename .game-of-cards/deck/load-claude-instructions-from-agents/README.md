---
title: load-claude-instructions-from-agents
summary: "Root `CLAUDE.md` contains the repo's main agent guidance while `AGENTS.md` only carries the GoC block. Move the shared guidance into `AGENTS.md`, reduce `CLAUDE.md` to a Claude Code import of `AGENTS.md`, and make `goc install`/`goc upgrade` apply the same import pattern for Claude-visible non-Claude briefing homes."
status: done
stage: null
contribution: medium
created: "2026-05-18T03:33:25Z"
closed_at: 2026-05-18T03:44:18Z
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [x] `AGENTS.md` contains the previously Claude-only repo guidance that is relevant to all LLM agents, while preserving the existing repo-local `uv run goc ...` note and GoC marker block.
  - [x] `CLAUDE.md` contains only an `@AGENTS.md` import (plus no duplicated repo guidance).
  - [x] Self-referential wording in the moved guidance no longer claims the canonical guidance lives in `CLAUDE.md` where `AGENTS.md` is the new source of truth.
  - [x] `goc install` and `goc upgrade` create or refresh a Claude Code `@<briefing-target>` import in `CLAUDE.md` when the installed agents include Claude and the briefing target is `AGENTS.md` or `CLAUDE.local.md`.
  - [x] The Claude-only path (`--briefing-target CLAUDE.md`) remains valid: the full briefing may live only in `CLAUDE.md`, with no required `AGENTS.md` file and no recursive import.
  - [x] Kickoff guidance says the install/upgrade primitive owns the import wiring, instead of telling agents to hand-roll a marker import snippet.
  - [x] Regression tests cover default Claude install, mixed Claude+Codex install, Claude-only briefing target, and upgrade-time import refresh.
  - [x] `uv run goc validate` passes.
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

Follow-up scope from the same request: `goc install` / `goc upgrade`
and kickoff should produce that same shape when Claude is one of the
installed agents and the chosen briefing home is not `CLAUDE.md`. The
exception is explicit Claude-only mode: if the repo chooses
`--briefing-target CLAUDE.md`, the full briefing can live in
`CLAUDE.md` and `AGENTS.md` can be omitted.

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

Then update the installer/upgrade path:

- If `agents` includes `claude` and `briefing_target` is `AGENTS.md`,
  write or refresh `CLAUDE.md` so Claude Code loads `@AGENTS.md`.
- If `agents` includes `claude` and `briefing_target` is
  `CLAUDE.local.md`, write or refresh `CLAUDE.md` so Claude Code loads
  `@CLAUDE.local.md`.
- If `briefing_target` is `CLAUDE.md`, keep the current Claude-only
  inline briefing behavior and do not require `AGENTS.md`.
- Update kickoff skill text to describe this behavior as owned by
  `goc install` / `goc upgrade`.

## Why It Matters

`AGENTS.md` is the cross-runtime instruction file for Codex and other
agent tools. Keeping most repo knowledge in `CLAUDE.md` hides it from
non-Claude agents and creates a misleading split between two root-level
instruction files. A one-line Claude import keeps Claude Code behavior
intact without duplicating or fragmenting the guidance.

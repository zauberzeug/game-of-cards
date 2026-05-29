---
title: provide-codex-plugin-for-skills-and-hooks
summary: "Provide a Codex plugin or equivalent Codex runtime package for Game of Cards skills and hooks, matching the Claude plugin direction where the runtime supports it. The goal is to avoid checked-in `.codex/skills` copies while preserving the same `goc`-backed workflow."
status: done
stage: null
contribution: low
created: 2026-05-05
closed_at: "2026-05-18T04:37:13Z"
human_gate: none
advances:
  - support-external-game-of-cards-state-location
  - publish-codex-plugin
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] Codex plugin/runtime extension format is confirmed and recorded
  - [x] Plugin or equivalent package supplies GoC skills/instructions without requiring checked-in `.codex/skills`
  - [x] Plugin-provided skills delegate to the installed `goc` CLI and `.game-of-cards` state
  - [x] Hook or prompt-routing support is implemented where Codex supports it, or explicitly documented as unsupported
  - [x] Behavior stays consistent with Claude plugin and optional repo-local harness modes
  - [x] Local smoke test confirms Codex can discover/use the GoC runtime affordance
  - [x] Docs explain install/use and limitations
  - [x] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Provide a Codex plugin for skills and hooks

## Why

Codex already has a first-class harness card, but the new direction is plugin-provided runtime affordances instead of checked-in generated skills. This card tracks the Codex side of that split.

## Session required

This needs a session because Codex plugin capabilities and hook equivalents must be verified before implementation. If Codex cannot provide a true plugin path, the accepted fallback should be documented explicitly.

## Decision

*Resolved 2026-05-18T04:09:46Z:* Ship GoC Codex support as a repo-hosted Codex plugin payload from zauberzeug/game-of-cards, with bundled skills, a bundled goc engine, and Codex hook support where the runtime supports it

*Reasoning:* User chose the GoC-official route and approved the proposed implementation shape; Codex docs now define plugins as installable distribution units for skills, apps, MCP servers, and optional hooks.

## Implementation

The usable Codex plugin now lives at `codex-plugin/` and is exposed by
`.agents/plugins/marketplace.json`.

What shipped:

- `.codex-plugin/plugin.json` points Codex at bundled skills and
  `hooks/hooks.json`.
- `codex-plugin/skills/` is generated from `goc/templates/skills/`
  with Codex frontmatter normalization and Codex-specific filtering.
- `codex-plugin/hooks/` contains the three GoC lifecycle hooks using
  `${PLUGIN_ROOT}` paths. Codex plugin hooks are documented as opt-in
  via `[features].plugin_hooks = true`.
- `codex-plugin/goc/` mirrors the Python engine, and `bin/goc` can run
  it via `PYTHONPATH` for plugin-aware launchers. Codex does not
  currently document plugin `bin/` auto-PATH behavior, so docs honestly
  keep the normal `goc` CLI as the command skills should call.
- `scripts/sync_plugin_assets.py` and `goc validate` now cover the
  Codex plugin payload and this repo's `.codex/skills/` dogfood copy.
- README, `goc.md`, `site/llms.txt`, release version rewriting, and
  version-surface tests now include the Codex plugin.

The reviewed local junk was not committed: the broken `.agents/skills`
tree used bad global substitutions, and `.codex/hooks.json` contained
absolute machine-local paths. Their useful content was replaced by the
tracked plugin payload.

Verification:

- `python3 scripts/sync_plugin_assets.py --check`
- `uv run goc validate --quiet`
- `PYTHONPATH=codex-plugin python3 -m goc.cli --version`
- `codex-plugin/bin/goc --version`
- `uv run python -m pytest`

---
title: bundle-goc-engine-inside-plugin-payload
summary: "Ship the `goc` engine (engine.py + cli.py + schema.yaml + templates) inside the plugin payload itself so the consuming repo never needs `uv tool install game-of-cards` or `pipx install game-of-cards` for the CLI to be available. Today's `plugin-bootstraps-cli-and-project-state-on-first-use` (done) installs goc via `uv tool install` as a fallback. Bundling removes one more 'opt-in to my machine' step for first-time evaluators: no global PyPI install, no PATH pollution, the plugin is fully self-contained."
status: open
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: session
advances:
  - ship-game-of-cards-as-cross-agent-cli
  - support-external-game-of-cards-state-location
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] Plugin payload includes the goc engine such that skills can invoke `goc` without the binary being on the user's PATH
  - [ ] Decision recorded on the invocation form: vendored entry point (`${CLAUDE_PLUGIN_ROOT}/bin/goc`), `python -m goc` against a vendored package, or zipapp; the chosen form is callable from skills without leaking absolute paths into card content or commits
  - [ ] First-run experience for a fresh repo: `/plugin install game-of-cards@…` → user prompts agent → bootstrap creates `.game-of-cards/`. Zero `uv tool install` / `pipx install` steps required. (`uv tool install game-of-cards` remains documented as the alternative for non-plugin consumers / CI without plugin support)
  - [ ] AGENTS.md / CLAUDE.md GoC blocks reflect the new invocation form so agents discover it correctly on cold reads
  - [ ] Existing `plugin-bootstraps-cli-and-project-state-on-first-use` flow still works for users who already have `goc` on PATH — the bundled engine is the new default, not a replacement that breaks existing setups
  - [ ] `uv run goc validate` passes
---

# Bundle goc engine inside plugin payload

## Why

The current bootstrap flow asks the user to install `game-of-cards`
globally via `uv tool install` (with `pipx` fallback) before the CLI
is callable. For users evaluating the tool on a library or strictly
controlled repo, every "install something globally" step is a
disqualifier — it pollutes their dev environment with an alpha tool
they may not keep.

If the engine ships inside the plugin, installing the plugin is the
only opt-in: marketplace install, then prompt the agent. No global
package, no PATH manipulation.

## Why session-gated

Open design questions:

1. Plugin payload size — `goc/templates/` is non-trivial; is bundling
   the whole package acceptable, or do we ship a slim engine and
   let the templates stay in the marketplace ref?
2. Python invocation: marketplaces don't guarantee a Python runtime;
   skills today rely on shell + `python` being available. How
   robust is `python -m goc.cli` vs. a zipapp shipped as `bin/goc`?
3. Does `pyproject.toml` need a separate "engine-only" extra so the
   plugin can vendor a minimal subset without `click` / template
   tree if they're not needed at runtime?
4. Interaction with `generate-plugin-payloads-from-templates-on-release`:
   if plugins are generated, the engine bundle is also a generated
   artefact and needs to live in the same generation step.

## Cross-references

- `plugin-bootstraps-cli-and-project-state-on-first-use` (done) —
  current bootstrap flow this card extends
- `claude-install-defaults-to-plugin-path` (done) — established the
  plugin-as-default direction
- `support-external-game-of-cards-state-location` (active) —
  related path-resolution work

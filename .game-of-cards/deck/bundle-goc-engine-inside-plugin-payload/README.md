---
title: bundle-goc-engine-inside-plugin-payload
summary: "Ship the `goc` engine (engine.py + cli.py + schema.yaml + templates) inside the plugin payload itself so the consuming repo never needs `uv tool install game-of-cards` or `pipx install game-of-cards` for the CLI to be available. Today's `plugin-bootstraps-cli-and-project-state-on-first-use` (done) installs goc via `uv tool install` as a fallback. Bundling removes one more 'opt-in to my machine' step for first-time evaluators: no global PyPI install, no PATH pollution, the plugin is fully self-contained."
status: done
stage: null
contribution: medium
created: 2026-05-07
closed_at: 2026-05-08
human_gate: session
advances:
  - ship-game-of-cards-as-cross-agent-cli
  - support-external-game-of-cards-state-location
  - add-readme-to-claude-code-plugin
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] Plugin payload includes the goc engine such that skills can invoke `goc` without the binary being on the user's PATH (`claude-plugin/goc/` mirrors `goc/`; `claude-plugin/bin/goc` shell wrapper resolves the bundled package via `uv run --project ${PLUGIN_ROOT}`; Claude Code auto-prepends the plugin's `bin/` to the Bash tool's PATH)
  - [x] Decision recorded on the invocation form: vendored entry point (`${CLAUDE_PLUGIN_ROOT}/bin/goc`), `python -m goc` against a vendored package, or zipapp; the chosen form is callable from skills without leaking absolute paths into card content or commits (Decision section below: `bin/goc` shell wrapper invoking `uv run --project`. Skill bodies keep calling plain `goc <verb>`; no `${CLAUDE_PLUGIN_ROOT}` leaks into skills or commits.)
  - [x] First-run experience for a fresh repo: `/plugin install game-of-cards@…` → user prompts agent → bootstrap creates `.game-of-cards/`. Zero `uv tool install` / `pipx install` steps required. (`uv tool install game-of-cards` remains documented as the alternative for non-plugin consumers / CI without plugin support)
  - [x] AGENTS.md / CLAUDE.md GoC blocks reflect the new invocation form so agents discover it correctly on cold reads (the invocation form `goc <verb>` is unchanged; CLAUDE.md "Plugin assets are duplicated" section updated to document the new triple-duplicate, and a new section "Plugin runs goc from a vendored engine" explains the wrapper. plugin.json + marketplace.json descriptions updated to reflect bundled engine.)
  - [x] Existing `plugin-bootstraps-cli-and-project-state-on-first-use` flow still works for users who already have `goc` on PATH — the bundled engine is the new default, not a replacement that breaks existing setups (verified: a system-installed `goc` continues to work; the plugin's `bin/goc` takes precedence on PATH when the plugin is enabled, but the existing `uv tool install` recipe remains valid for non-plugin consumers / CI environments. The wrapper exits 127 with a clear error when uv is missing.)
  - [x] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
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

## Decision

Resolved 2026-05-08: the four design questions collapsed once Claude
Code's plugin docs were consulted. The runtime auto-prepends a plugin's
`bin/` to the Bash tool's PATH, which removes the need for hooks or
explicit path-prefixing in skill bodies — `goc <verb>` continues to
work verbatim.

**Q1 (payload size).** Bundle the entire `goc/` package
(engine + cli + install + schema + templates) at `claude-plugin/goc/`.
~150 KB. The "slim engine" alternative was over-engineering — every
verb that uses `importlib.resources.files('goc.templates')` continues
to work because the templates ship inside the bundled package.

**Q2 (invocation form).** A shell wrapper at `claude-plugin/bin/goc`
that resolves `PLUGIN_ROOT` relative to itself and `exec`s
`uv run --quiet --project "$PLUGIN_ROOT" goc "$@"`. Claude Code adds
the plugin's `bin/` to PATH, so skill bodies keep their existing
`goc <verb>` syntax — no `${CLAUDE_PLUGIN_ROOT}` strings leak into
skill markdown or commit messages. The wrapper requires `uv` on the
host PATH; without it, the wrapper exits 127 with a clear pointer to
`https://docs.astral.sh/uv/` and the `pipx install game-of-cards`
fallback.

**Q3 (engine-only extra).** Not needed. The plugin's
`claude-plugin/pyproject.toml` declares the same two runtime deps
(`click>=8.1`, `pyyaml>=6.0`) that the package needs. uv builds an
isolated venv at `claude-plugin/.venv/` (gitignored) on first call.

**Q4 (interaction with generation).** Coupled but not blocking. The
existing CI byte-for-byte tripwire is extended from two pairs to
three (skills, hook scripts, full bundle), keeping all duplicates in
sync. When `generate-plugin-payloads-from-templates-on-release`
later closes, generation will collapse all three duplicates to a
single source-of-truth plus generated build artefacts.

**Why uv-as-prereq is acceptable.** The card's stated goal is
removing "global PyPI install of `game-of-cards`" — not all global
tooling. `uv` is already a project prerequisite (CI runs `uv run`,
README documents `uv tool install` for non-plugin consumers). The
bundle trades "user installs game-of-cards globally" for
"runtime resolves game-of-cards from inside the plugin via uv."
First-time evaluators no longer pollute their environment with the
goc package itself; uv stays out of the way as a generic Python
dep manager.

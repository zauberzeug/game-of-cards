---
title: codex-plugin-skills-cannot-find-bundled-goc-cli
summary: "The GoC plugin cache contains a working bundled `bin/goc` wrapper, but Codex skill execution does not put that wrapper on shell PATH. Downstream Codex agents therefore load the GoC skills successfully, then report that `goc` / `uv run goc` cannot spawn and fall back to editing deck files directly."
status: done
stage: null
contribution: medium
created: "2026-06-05T10:37:14Z"
closed_at: "2026-06-09T04:29:29Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduction covers a downstream repo with no global `goc` on PATH and no GoC package dependency where the plugin-cache wrapper works by absolute path.
  - [x] MECHANICAL: Codex-specific GoC skill guidance no longer implies that plugin-provided skills automatically deliver a shell-visible `goc` command.
  - [x] MECHANICAL: Codex command-resolution guidance gives agents an executable path that does not require creating a global `~/.local/bin/goc` shim.
  - [x] EMPIRICAL: downstream smoke in a non-GoC repo can run the bundled engine through the documented Codex path and no longer falls back to direct deck-file mutation.
  - [x] EMPIRICAL: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass.
worker: {who: "claude[bot]", where: main}
---

# Codex plugin skills cannot find bundled GoC CLI

## Location

- `codex-plugin/bin/goc` — working wrapper that invokes the bundled engine.
- `codex-plugin/README.md:26-30` — already notes that Codex does not document
  plugin `bin/` auto-PATH behavior.
- `goc/templates/skills/codex-kickoff/SKILL.md:63-85` — tells agents to try
  `goc`, then `uv run goc`, then a manually supplied plugin path.
- Plugin cache example:
  `/Users/rodja/.codex/plugins/cache/zauberzeug-claude/game-of-cards/0.0.23/bin/goc`

## What's broken

The GoC plugin payload bundles a functional CLI wrapper, but Codex skill
execution does not make that wrapper discoverable as `goc` on shell PATH.
The skills still contain many bare `goc ...` commands inherited from the
Claude/plugin model, where plugin `bin/` directories are expected to be
visible to the Bash tool.

In a downstream repo with no global GoC install:

```text
goc --help
# zsh: command not found: goc

uv run goc --help
# error: Failed to spawn: `goc`
#   Caused by: No such file or directory (os error 2)

/Users/rodja/.codex/plugins/cache/zauberzeug-claude/game-of-cards/0.0.23/bin/goc --help
# works
```

That makes the agent's fallback understandable but wrong for GoC workflow:
it edits deck files directly because the command surface described by the
loaded skills is not callable.

## Why it matters

The CLI is the engine that enforces card schema, relationship invariants,
status transitions, DoD closure checks, and auto-commit policy. Direct
deck-file mutation bypasses those contracts. A Codex plugin install that loads
the GoC skills but cannot run `goc` leaves agents with the method text but
without the runtime that makes the method safe.

This should not be solved by asking users to create a global
`~/.local/bin/goc` shim. The plugin already contains the engine; Codex-specific
guidance needs an invocation path that reaches the bundled wrapper or otherwise
sets `PYTHONPATH` to the plugin root explicitly.

## Fix direction

Codex-specific skill guidance should distinguish three cases:

1. **Global CLI available**: use `goc ...`.
2. **Game-of-Cards source checkout**: use `uv run goc ...` as this repo's
   `AGENTS.md` requires.
3. **Codex plugin-only install**: use the plugin-bundled wrapper or
   `PYTHONPATH=<plugin-root> python3 -m goc.cli ...`; do not assume plugin
   `bin/` is on PATH.

The remaining design choice is how a Codex-loaded skill should discover
`<plugin-root>` robustly. Possible routes:

- Codex exposes a plugin-root environment variable or manifest field the skill
  can reference.
- The Codex plugin payload ships a small helper instruction that derives the
  root from the skill path shown in Codex's loaded-skill metadata.
- The generic skills stay host-neutral, but Codex-specific guidance teaches the
  model to use the absolute cached wrapper path when available.

## Artifacts

- `tests/test_codex_plugin_bundled_cli.py` — runs the bundled
  `codex-plugin/bin/goc` wrapper and `PYTHONPATH=<root> python3 -m
  goc.cli` from a non-GoC temp cwd (the reproduction), and asserts the
  corrected `codex-kickoff` guidance.
- `goc/templates/skills/codex-kickoff/SKILL.md` Stage 2 — rewritten
  into a three-case command-resolution section (global / checkout /
  plugin-only), deriving the plugin root from the skill's own loaded
  path with `${PLUGIN_ROOT}` preferred when exported.

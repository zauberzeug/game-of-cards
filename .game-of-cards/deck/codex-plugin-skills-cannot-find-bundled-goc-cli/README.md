---
title: codex-plugin-skills-cannot-find-bundled-goc-cli
summary: "The GoC plugin cache contains a working bundled `bin/goc` wrapper, but Codex skill execution does not put that wrapper on shell PATH. Downstream Codex agents therefore load the GoC skills successfully, then report that `goc` / `uv run goc` cannot spawn and fall back to editing deck files directly."
status: done
stage: null
contribution: medium
created: "2026-06-05T10:37:14Z"
closed_at: "2026-06-09T06:49:44Z"
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
worker: {who: Rodja Trappe, where: main}
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

Codex-specific skill guidance now distinguishes three cases:

1. **Global CLI available**: use `goc ...`.
2. **Game-of-Cards source checkout**: use `uv run goc ...` as this repo's
   `AGENTS.md` requires.
3. **Codex plugin-only install**: use the shipped
   `<plugin-root>/skills/_goc-bootstrap.sh ...` helper, which invokes the
   sibling `bin/goc` wrapper and therefore does not require a global shim or
   shell-visible plugin `bin/`.

The Codex skill renderer injects a `## Codex GoC Command` resolver block into
every generated Codex skill. The block tells agents to derive the plugin root
from the loaded skill path when available, or locate the helper under
`$HOME/.codex/plugins/cache` otherwise. `codex-plugin/skills/_goc-bootstrap.sh`
is shipped as a real plugin payload file, and the bootstrap also works when
executed from the plugin cache because it detects `../bin/goc` relative to its
own path.

The engine's mirror-parity check and `scripts/sync_plugin_assets.py --check`
both understand the Codex-rendered skill text plus the `_goc-bootstrap.sh`
sidecar, so a future template edit cannot silently leave plugin skills stale.

## Artifacts

- `tests.test_install.ClaudeHarnessInstallTest.test_bootstrap_wrapper_execs_plugin_sibling_cli_without_path_goc`
  covers a downstream repo with no `goc` on `PATH` and a fake plugin-cache
  sibling `bin/goc`.

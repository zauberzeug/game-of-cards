---
title: vendored-hooks-bake-uv-into-claude-settings-breaking-pipx-only-installs
summary: "`goc install --local-skills` writes `.claude/settings.json` hook commands like `uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py`, forcing every Claude Code session to have `uv` on PATH. README documents `pipx install game-of-cards` as a valid install path that does NOT bring `uv`, so a pipx-only consumer's SessionStart, UserPromptSubmit, and Stop hooks all crash with `uv: not found` on every session. The hook scripts are stdlib-only (no `import goc`), so `python3` would work identically — and the plugin path already uses `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/...` in `claude-plugin/hooks/hooks.json`."
status: done
stage: null
contribution: medium
created: "2026-05-29T13:40:26Z"
closed_at: "2026-05-29T13:46:29Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — with `uv` removed from PATH, the rendered hook command `python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py` (post-fix) runs the hook cleanly, whereas the pre-fix `uv run python …` command fails with `uv: not found`.
  - [x] MECHANICAL: `GOC_CLAUDE_HOOKS` in `goc/install.py` (currently lines 539-543) drops the `uv run ` prefix and registers `python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/<script>.py` — matching the plugin payload at `claude-plugin/hooks/hooks.json`.
  - [x] MECHANICAL: the three test cases in `tests/test_install.py` that pin the hook command string (lines 187, 802, 806, 832, 862, 866, 886) update to the new `python3 …` shape; no test still asserts the `uv run python` literal.
  - [x] MECHANICAL: this repo's own `.claude/settings.json` is regenerated (or hand-edited) to the new shape so the dogfood install matches what consumers get.
  - [x] PROCESS: `uv run goc validate --quiet` clean; `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` clean.
worker: {who: "claude[bot]", where: main}
---

# Vendored hooks bake `uv` into `.claude/settings.json`, breaking pipx-only installs

## Location

- Hook command source-of-truth: `goc/install.py:539-543` (`GOC_CLAUDE_HOOKS`)
- Writer that copies it into consumer settings: `goc/install.py:556` (`_merge_claude_settings`)
- Plugin-path counterpart (already uses `python3`): `claude-plugin/hooks/hooks.json`
- Tests pinning the current command literal: `tests/test_install.py:187, 802, 806, 832, 862, 866, 886`

## What's broken

`goc/install.py:539-543` defines the canonical hook commands written into
`.claude/settings.json` by `goc install --local-skills`:

```python
GOC_CLAUDE_HOOKS: dict[str, str] = {
    "SessionStart": "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
    "UserPromptSubmit": "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py",
    "Stop": "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py",
}
```

The `uv run python` prefix means every Claude Code session needs `uv`
on PATH for these three hooks to fire. But `README.md:46` lists pipx
as a documented install path:

> **Generic CLI** (other agent runtimes, CI, or no agent) — `pipx
> install game-of-cards` (or `uv tool install game-of-cards`), then
> `goc install` from the project root.

`pipx install game-of-cards` installs `goc` into pipx's bin directory.
It does **not** install `uv`. So a pipx-only consumer who runs `goc
install --local-skills` ends up with hook registrations that fail at
SessionStart, UserPromptSubmit, and Stop with `uv: not found`.

The hook scripts themselves are entirely stdlib — they don't `import
goc`, don't pin a Python version beyond stdlib availability, and
don't need a project venv. Verified by grep:

```
$ grep -E "^(import |from )" goc/templates/hooks/*.py
goc/templates/hooks/pattern_generalization_check.py:import json
goc/templates/hooks/pattern_generalization_check.py:import os
goc/templates/hooks/pattern_generalization_check.py:import re
goc/templates/hooks/pattern_generalization_check.py:import sys
goc/templates/hooks/pattern_generalization_check.py:from pathlib import Path
goc/templates/hooks/deck_prompt_router.py:import json …
goc/templates/hooks/deck_session_start.py:import json …
```

The plugin payload at `claude-plugin/hooks/hooks.json` already reflects
this — it ships `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py` with
no `uv` involvement. So the vendored install is the lone outlier that
embeds `uv` for no functional reason.

## Empirical evidence

Pre-fix, `reproduce.py` asserted that the vendored command failed
without `uv` on PATH (`rc=127, uv: not found`). Post-fix, the same
script asserts the rendered command runs cleanly:

```
$ uv run python .game-of-cards/deck/vendored-hooks-bake-uv-into-claude-settings-breaking-pipx-only-installs/reproduce.py
hook scripts use only stdlib: deck_prompt_router.py, deck_session_start.py, pattern_generalization_check.py
plugin hooks already use python3 — no uv: ['python3 ${CLAUDE_PLUGIN_ROOT}/hooks/deck_session_start.py', 'python3 ${CLAUDE_PLUGIN_ROOT}/hooks/deck_prompt_router.py', 'python3 ${CLAUDE_PLUGIN_ROOT}/hooks/pattern_generalization_check.py']
vendored install uses python3: SessionStart=python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py UserPromptSubmit=python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py Stop=python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py
without uv on PATH the vendored command runs cleanly: rc=0
```

## Why it matters

`pipx install game-of-cards` is one of the two install recipes the
top-of-tree README documents for "no agent" / "generic CLI" consumers
(README.md:46). For any such consumer who does not separately install
`uv`:

- `SessionStart` hook (the active-card reminder) silently dies at
  start of every Claude Code session.
- `UserPromptSubmit` hook (the deck-first prompt router) dies on
  every prompt — the routing logic the rest of the GoC methodology
  depends on is missing.
- `Stop` hook (pattern-generalization self-assessment) dies after
  every model turn.

These hooks are advertised as the silent runtime that ties the deck
to the agent's working loop. They go from "installed and silent" to
"installed and broken" because of an unnecessary `uv run` prefix.

**Reachability path.** The hook commands are written by
`_merge_claude_settings` in `goc/install.py:556` during the standard
`goc install --local-skills` path documented in `README.md` and the
generated `CLAUDE.md` / `AGENTS.md` blocks. Anyone following the
"pipx → `goc install --local-skills`" recipe hits this immediately on
their first Claude Code session in the repo.

## Fix

Change `GOC_CLAUDE_HOOKS` in `goc/install.py:539-543` to drop the
`uv run ` prefix:

```python
GOC_CLAUDE_HOOKS: dict[str, str] = {
    "SessionStart": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
    "UserPromptSubmit": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py",
    "Stop": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py",
}
```

This matches `claude-plugin/hooks/hooks.json` exactly (modulo the
`${CLAUDE_PROJECT_DIR}` vs `${CLAUDE_PLUGIN_ROOT}` path root) — the
same `python3` choice the plugin path already validated.

Update the `uv run python` literals in `tests/test_install.py` (lines
187, 802, 806, 832, 862, 866, 886) to the new shape. Regenerate this
repo's own `.claude/settings.json` (or hand-edit) so the dogfood
install matches what consumers receive.

The `python3` binary is a near-universal assumption on macOS/Linux
dev machines and inside the Claude Code runtime. If a future
defect surfaces around very old systems lacking `python3`, that's a
separate card on Python-version detection — out of scope here.

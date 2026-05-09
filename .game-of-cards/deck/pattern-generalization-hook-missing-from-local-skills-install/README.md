---
title: pattern-generalization-hook-missing-from-local-skills-install
summary: "`goc/install.py` registers the Stop hook `pattern_generalization_check.py` in `.claude/settings.json` for every `--local-skills` install (via `GOC_CLAUDE_HOOKS` and `_merge_claude_settings`), but the hook script itself is never copied to `.claude/hooks/`. The claude manifest's `files` array at `goc/templates/agents/claude/manifest.json` only lists `deck_prompt_router.py` and `deck_session_start.py`. Result: every code-mutating turn ends with the Stop hook firing and immediately failing with `python: can't open file '.../pattern_generalization_check.py': [Errno 2] No such file or directory`. Plugin-path users are unaffected because `claude-plugin/hooks/pattern_generalization_check.py` is a real file and is auto-discovered. Found during a 2026-05-09 review."
status: open
stage: null
contribution: high
created: 2026-05-09
closed_at: null
human_gate: none
advances:
  - list-game-of-cards-on-anthropic-community-marketplace
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] Add `pattern_generalization_check.py` to the `files` array in `goc/templates/agents/claude/manifest.json` (source `hooks/pattern_generalization_check.py`, target `.claude/hooks/pattern_generalization_check.py`)
  - [ ] Add the source-of-truth → consumer-copy pair to `validate_plugin_mirror_parity` in `goc/engine.py:549-560` so `goc validate` catches future drift on this file locally
  - [ ] Regression test: `goc install --local-skills` in a tmpdir produces `.claude/hooks/pattern_generalization_check.py` and `.claude/settings.json` references it; the regression test runs in CI alongside the existing install tests
  - [ ] Manual verification: run `goc install --local-skills` in a throwaway repo, end a code-mutating turn, observe the Stop hook executes without "file not found"
  - [ ] `uv run goc validate` passes
---

# Pattern-generalization hook missing from --local-skills install

## What's broken

Two surfaces register `pattern_generalization_check.py`:

1. `goc/install.py:278-280` defines `GOC_CLAUDE_HOOKS` mapping the
   Stop event to `python ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py`.
   `_merge_claude_settings` writes that mapping into `.claude/settings.json`
   on every `--local-skills` install.
2. `claude-plugin/hooks/hooks.json` registers the same hook against the
   plugin-bundled copy at `claude-plugin/hooks/pattern_generalization_check.py`.

One surface installs the file:

- `claude-plugin/hooks/pattern_generalization_check.py` exists as a
  real file (auto-synced from `goc/templates/hooks/pattern_generalization_check.py`
  by `scripts/sync_plugin_assets.py`).

One surface fails to:

- The claude manifest at `goc/templates/agents/claude/manifest.json`
  drives the `--local-skills` file copy. Its `files` array lists
  `deck_prompt_router.py` and `deck_session_start.py` and stops there.
  The third hook never lands in `.claude/hooks/`.

End state: a `--local-skills` user has `.claude/settings.json`
referencing `.claude/hooks/pattern_generalization_check.py`, but the
file does not exist. Every code-mutating turn fires the Stop hook
and produces a `FileNotFoundError`.

## Tripwire gap

`validate_plugin_mirror_parity` in `goc/engine.py:549-560` enumerates
the byte-for-byte parity pairs the local `goc validate` should check.
It covers `deck_prompt_router.py` and `deck_session_start.py` but not
`pattern_generalization_check.py`. `scripts/sync_plugin_assets.py`
covers all three (lines 35-37), so CI catches plugin-mirror drift on
the file. But the local-developer tripwire reports false-clean for
the missing file specifically. Adding the third pair to the validate
function is a one-line fix and is included in the DoD.

## Why this card is gate=none

The fix is purely additive (one entry in a manifest, one entry in a
validator pair list, one regression test). No design decision is
needed. Any pull-card agent can claim and ship it.

## Cross-references

- `agent-flags-unfiled-pattern-generalization-cards-before-stop`
  (done) — the card that introduced the hook itself, completed
  2026-05-06; did not cover the manifest registration for the
  `--local-skills` consumer path
- `extend-skill-parity-tripwire-to-claude-plugin-mirrors` (done) —
  added `validate_plugin_mirror_parity`; this card extends its
  coverage to the third hook file
- `derive-claude-hook-manifest-from-templates` (open) — generalization
  card that, if accepted, would prevent this class of bug entirely
  by deriving the hook list mechanically

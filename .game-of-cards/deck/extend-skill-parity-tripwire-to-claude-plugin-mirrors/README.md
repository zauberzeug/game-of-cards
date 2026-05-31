---
title: extend-skill-parity-tripwire-to-claude-plugin-mirrors
summary: "The skill-parity tripwire (`validate_skill_dir_parity` in `goc/engine.py`) only checks consumer skill copies under `.claude/skills/` and `.codex/skills/`. It does not check the `claude-plugin/` mirrors that ship the bundled engine — `claude-plugin/skills/`, `claude-plugin/hooks/*.py`, and the nested `claude-plugin/goc/` tree. The byte-for-byte CI step does check those, but only after push, so contributors discover drift in the red CI run rather than locally. Two drift incidents in three days (kickoff SKILL.md after `make-kickoff-idempotent-on-restart`; the same file again after `bundle-goc-engine-inside-plugin-payload`) confirm the gap is real. Extend the local tripwire to mirror the CI check so drift is caught pre-push."
status: done
stage: null
contribution: medium
created: 2026-05-08
closed_at: 2026-05-08
human_gate: none
advances:
  - prevent-skill-rename-from-breaking-ci-silently
  - derive-claude-hook-manifest-from-templates
advanced_by:
  - validate-plugin-mirror-parity-uses-shallow-filecmp-missing-content-drift
tags: [bug, infra]
definition_of_done: |
  - [x] `goc validate` (or a dedicated `goc validate --plugin-mirrors` sub-check) reproduces the CI byte-for-byte parity check across all four mirror pairs: `goc/templates/skills` ↔ `claude-plugin/skills`, the two hook scripts, and `goc` ↔ `claude-plugin/goc`
  - [x] The check fails locally with the same drift report shape CI prints, so contributors don't have to read CI logs to diagnose
  - [x] Pre-commit runs the check (extend the existing `goc validate` hook in `.pre-commit-config.yaml`)
  - [x] A regression test deliberately breaks one of the four mirror pairs and asserts the new check fails with a useful message
  - [x] CI's `Verify plugin assets match templates byte-for-byte` step remains as belt-and-braces, but the local check is now first-line defence
  - [x] `uv run goc validate` and the full test suite pass under a CI-clean env (`HOME=$(mktemp -d)`)
worker: {who: "claude[bot]", where: main}
---

# Extend skill-parity tripwire to claude-plugin mirrors

## Why

`prevent-skill-rename-from-breaking-ci-silently` (closed 2026-05-08) added
a `goc validate` sub-check via `validate_skill_dir_parity` that flags
drift between `goc/templates/skills/` and the consumer copies under
`.claude/skills/` and `.codex/skills/`. That fixed the contributor-facing
case where renaming a skill in templates without re-running `goc upgrade`
left the consumer copies stale.

It did not extend the same check to the **plugin mirrors**: the
`claude-plugin/` payload that ships the bundled engine to Claude Code
plugin consumers. Those mirrors are byte-for-byte duplicates of two
trees:

- Flat: `claude-plugin/skills/` ↔ `goc/templates/skills/` (auto-discovered
  by Claude Code's plugin runtime).
- Nested: `claude-plugin/goc/` ↔ `goc/` (resolved by the bundled engine
  via `importlib.resources` when running under `bin/goc`).

CI verifies all four mirror pairs byte-for-byte
(`.github/workflows/ci.yml` → "Verify plugin assets match templates
byte-for-byte"). Local `goc validate` does not. Result: contributors
ship a commit that passes locally and fails in CI minutes later.

This card recently broke twice:

- `bundle-goc-engine-inside-plugin-payload` (introduced the nested mirror)
- `make-kickoff-idempotent-on-restart` (updated `goc/templates/skills/kickoff/SKILL.md`
  and `claude-plugin/skills/kickoff/SKILL.md`, but missed the nested
  `claude-plugin/goc/templates/skills/kickoff/SKILL.md`)

Both required follow-up commits to restore parity. Catching the drift
locally before push is the whole point of having a tripwire — extending
it to the plugin mirrors closes the loop.

## Approach sketch

The CI step already implements the check in inline Python; lift that
logic into `goc/engine.py` as a sibling to `validate_skill_dir_parity`,
e.g. `validate_plugin_mirror_parity`, and call it from the same
`validate` entry point. The four mirror pairs are stable enough to
hardcode (the canonical list lives in CLAUDE.md's "Plugin assets are
duplicated" table); deriving them from a config file is overkill for
four entries.

A future iteration may unify both checks under a single
`validate_byte_parity` that takes a list of `(src, dst)` pairs, but that
refactor is not required for the fix.

## Cross-references

- `prevent-skill-rename-from-breaking-ci-silently` — the parent fix that
  this extends.
- `generate-plugin-payloads-from-templates-on-release` — the larger
  redesign that would collapse the duplication entirely; until that
  ships, the mirrors remain real files and need a tripwire.

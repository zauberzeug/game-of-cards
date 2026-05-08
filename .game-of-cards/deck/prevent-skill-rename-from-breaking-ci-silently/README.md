---
title: prevent-skill-rename-from-breaking-ci-silently
summary: "The canonical skill set lives at `goc/templates/skills/` but is duplicated as inline lists in `tests/test_install.SKILL_NAMES`, `.github/workflows/ci.yml`'s package-data check, and the dogfood consumer copies under `.claude/skills/` and `.codex/skills/`. A skill rename or addition that touches templates without lockstep edits to all duplicates passes local checks and breaks CI. Eliminate the duplication where possible (derive at runtime) and add a pre-commit tripwire for the cases where derivation isn't an option."
status: done
stage: null
contribution: medium
created: 2026-05-08
closed_at: 2026-05-08
human_gate: none
advances: []
advanced_by:
  - extend-skill-parity-tripwire-to-claude-plugin-mirrors
tags: [bug]
definition_of_done: |
  - [x] `tests/test_install.SKILL_NAMES` is replaced with a runtime derivation that reads `goc/templates/skills/` directly — no inline name list to drift
  - [x] `.github/workflows/ci.yml`'s "Verify package data ships templates" step iterates the package-data skills directory rather than a hardcoded list
  - [x] A pre-commit hook (or new `goc validate` sub-check) fails when the skill-name set under `.claude/skills/` or `.codex/skills/` differs from `goc/templates/skills/`. The check runs locally before push, not just in CI
  - [x] A regression test exercises the tripwire: simulate a stale consumer copy and assert the check fails with a useful message
  - [x] `uv run goc validate` and the full test suite pass under a CI-clean env (`HOME=$(mktemp -d)`)
  - [x] The fix is verified by deliberately renaming a skill in templates locally and confirming the new tripwire catches the drift before push
worker: {who: Rodja Trappe, where: main}
---

# Prevent skill renames from breaking CI silently

## Why

The 2026-05-08 merge of the `extend-deck` → `audit-deck` and
`improve-deck` → `refine-deck` rename (plus the additions of `standup`,
`retrospective`, and the `bootstrap` → `kickoff` codex variant) updated
`goc/templates/skills/` and the `claude-plugin/` payload, but left
three other places stale:

1. `tests/test_install.SKILL_NAMES` — hardcoded list of 11 skill names
   that drove two test methods into `FileNotFoundError`.
2. `.github/workflows/ci.yml`'s "Verify package data ships templates"
   step — same hardcoded 11-skill list inline in the workflow YAML.
3. `.claude/skills/` and `.codex/skills/` — the dogfood consumer copies
   that the test suite checks for parity. These weren't renamed at all;
   they kept the old skill folders alongside the templates' new layout.

All three sites passed pre-commit locally (because pre-commit only runs
`goc validate`), passed the developer's own test runs (because the
local checkout had whichever subset matched the developer's manual
edits), and failed only when CI ran the full matrix. The merge needed
three follow-up commits to recover. The byte-for-byte plugin-asset
tripwire that already exists for `claude-plugin/` is exactly the kind
of guard we lack here, and the symmetry is not accidental — both
classes are "source of truth + duplicates that drift on rename".

## Scope

In:

- Replace `SKILL_NAMES` in `tests/test_install.py` with a runtime
  derivation that reads `goc/templates/skills/` (or `importlib.resources`
  via the same path the engine uses) and returns the set of subdirectory
  names containing a `SKILL.md`.
- Replace the inline `skills = [...]` in the CI workflow's package-data
  check with the same runtime derivation.
- Add a pre-commit-time check (either a new pre-commit hook entry or a
  sub-check inside `goc validate`) that asserts the skill-name set under
  `.claude/skills/` and `.codex/skills/` matches `goc/templates/skills/`.
  When the sets differ, the check fails with a message naming the
  offending paths and pointing at `goc upgrade --keep-local-skills` as
  the recovery command.
- A regression test that constructs a tmpdir with a stale consumer copy
  and asserts the new check rejects it.

Out:

- The byte-for-byte plugin-asset duplication under `claude-plugin/` —
  already covered by the existing CI tripwire and slated for removal
  via `generate-plugin-payloads-from-templates-on-release`.
- Inline skill-name mentions in user-facing prose (CLAUDE.md, plugin
  README, game_of_cards/README.md). Those are individually-named
  references in editorial copy, not enumerable lists; a tripwire for
  them would be high-noise. If we want that later, file a separate
  card.
- Renaming the existing pre-commit `goc validate` hook or restructuring
  pre-commit configuration beyond adding the new check.

## Approach

The drift class has two failure modes that need different fixes:

**Mechanical lists** (test, CI workflow): these are arrays of strings
that should never have been hardcoded. Replace each with a one-liner
that lists the children of `goc/templates/skills/`. Result: zero source
of duplication, zero possible drift.

**Consumer-copy directories** (`.claude/skills/`, `.codex/skills/`):
these are real files on disk that must exist with specific names for
the dogfood install to work. Derivation isn't an option — the files
have to exist. Add a tripwire (pre-commit hook or `goc validate`
sub-check) that compares the on-disk skill-name set under each consumer
root to the template set and fails on mismatch. The natural home is
`goc validate` since pre-commit already runs it; adding the check there
means no new pre-commit entry to maintain. Recovery instruction in the
error message: `goc upgrade --keep-local-skills`.

## Notes

- Today's pre-commit config has a single hook: `goc validate`. Extending
  it is a one-line change in `goc/engine.py`'s validator, no new
  pre-commit entry needed.
- The byte-for-byte plugin-asset check at CI time is the architectural
  precedent here. The new check is the same idea applied one layer
  earlier (templates → consumer copies, instead of templates → plugin
  payload).
- Watch for false-positives during a partial install where the user
  passed `--keep-local-skills` recently but templates moved on. The
  error message must clearly name the recovery command.

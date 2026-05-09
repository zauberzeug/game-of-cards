---
title: derive-claude-hook-manifest-from-templates
summary: "The hook list is hand-maintained in three places: `goc/templates/agents/claude/manifest.json` (drives `--local-skills` file copy), `goc/install.py:278-280` (`GOC_CLAUDE_HOOKS` mapping that writes settings.json), and `validate_plugin_mirror_parity` in `goc/engine.py:549-560` (pre-push tripwire). When the three lists drift, the registered hook fails at runtime. The 2026-05-09 review found exactly this drift for `pattern_generalization_check.py`. This is the same shape as `prevent-skill-rename-from-breaking-ci-silently` (done) and `extend-skill-parity-tripwire-to-claude-plugin-mirrors` (done) — a 'derived list' that wasn't actually derived. Apply the same generalization here: derive the hook list mechanically from `goc/templates/hooks/*.py`, or add a tripwire that asserts every script under that directory appears in all three lists."
status: open
stage: null
contribution: medium
created: 2026-05-09
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - prevent-skill-rename-from-breaking-ci-silently
  - extend-skill-parity-tripwire-to-claude-plugin-mirrors
tags: [story, infra]
definition_of_done: |
  - [ ] Approach chosen (see Decision required) and implemented
  - [ ] If derivation: `goc install --local-skills` no longer reads a hand-maintained manifest list of hooks; it iterates `goc/templates/hooks/*.py` directly. `GOC_CLAUDE_HOOKS` and the `validate_plugin_mirror_parity` pairs are computed from the same source
  - [ ] If tripwire: `goc validate` fails with a clear message when a script under `goc/templates/hooks/` is missing from any of the three registration sites; CI parity check unchanged
  - [ ] Regression test: add a placeholder `goc/templates/hooks/_test_hook.py` and assert the chosen mechanism either picks it up automatically (derivation) or rejects the missing registration (tripwire); remove the placeholder before merge
  - [ ] `uv run goc validate` and the full test suite pass under a CI-clean env (`HOME=$(mktemp -d)`)
---

# Derive Claude hook manifest from templates

## Why

Three sites in the codebase enumerate hooks:

1. **Manifest** — `goc/templates/agents/claude/manifest.json` drives the
   file copy step in `goc install --local-skills`. Its `files` array
   currently lists two hooks (`deck_prompt_router.py`,
   `deck_session_start.py`) and skips a third
   (`pattern_generalization_check.py`).
2. **Settings registration** — `GOC_CLAUDE_HOOKS` in
   `goc/install.py:278-280` is a Python dict mapping each event
   (`PreToolUse`, `Stop`, etc.) to the script path that handles it.
   Writes into `.claude/settings.json`.
3. **Parity tripwire** — `validate_plugin_mirror_parity` in
   `goc/engine.py:549-560` enumerates byte-equality pairs for local
   `goc validate`.

A new hook must land in all three lists. A missing hook in any one
produces a different failure mode:

- Missing from (1) → file not copied; runtime `FileNotFoundError`
- Missing from (2) → file copied but never invoked; silent no-op
- Missing from (3) → drift in any of the byte-equality pairs is
  discovered in CI rather than locally

The 2026-05-09 review caught the (1) and (3) drift for
`pattern_generalization_check.py`. There is no mechanism today to
catch (2) — it would surface as "the hook isn't firing for some
reason," diagnosed by hand.

This is structurally identical to the skill-rename problem already
solved by `prevent-skill-rename-from-breaking-ci-silently` (a derived
list replaces the hand-maintained one) and
`extend-skill-parity-tripwire-to-claude-plugin-mirrors` (a tripwire
catches drift between source-of-truth and consumer copies).

## Decision required

**A. Pure derivation.** Walk `goc/templates/hooks/*.py`, infer the
event from a header comment or filename convention (e.g., a
`# event: Stop` line in each script), and compute the three lists at
runtime. Manifest, `GOC_CLAUDE_HOOKS`, and the validator pairs all
read from the same in-process derivation. Pro: zero drift possible.
Con: introduces a header-comment convention, which is itself a
source of drift if a script is added without the convention.

**B. Hybrid (header convention + tripwire).** Same derivation as A
for the manifest and validator pairs, but `GOC_CLAUDE_HOOKS` keeps
the explicit dict (event mapping is genuinely informative and worth
seeing in source). Add a `validate_hook_registration` check that
asserts every script under `goc/templates/hooks/` has an entry in
the dict, and every dict entry points at a real file. Pro: keeps the
event-mapping legible; tripwire catches the case A's convention
misses. Con: two mechanisms instead of one.

**C. Pure tripwire (no derivation).** Keep all three lists
hand-maintained but add `validate_hook_registration` that fails
when the three lists' set of script names disagrees. Pro: smallest
change; preserves explicit lists. Con: doesn't prevent the
"contributor edits two of three lists, tripwire catches it on
validate" friction — one fewer step in the recovery loop than B.

A is the most robust but introduces a new convention. C is the
smallest change but keeps the redundancy. B is the natural compromise.

## Why decision gate

The "right" amount of derivation here depends on how often hooks are
added. If hooks are rarely added (the deck currently has 3, and the
plan does not call for many more), C is plausibly the right answer.
If we expect to add several more (per-runtime hooks, project-specific
hooks), A or B pays for itself. The user has the better signal on
expected rate-of-change.

## Cross-references

- `prevent-skill-rename-from-breaking-ci-silently` (done) — the
  parent pattern: derived skill list replaces hand-maintained one
- `extend-skill-parity-tripwire-to-claude-plugin-mirrors` (done) —
  the sibling pattern: tripwire across mirror pairs
- `pattern-generalization-hook-missing-from-local-skills-install`
  (open) — the immediate instance this card is generalizing from;
  shippable independently while this card waits on a decision

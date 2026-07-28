---
title: agents-md-mislabels-claude-settings-json-as-user-owned-permission-list
summary: "AGENTS.md's dogfood-sync section calls `.claude/settings.json` a \"project-specific permission allow-list\" that is \"meant to be customized per repo\", grouping it with the user-owned `.game-of-cards/` content stubs. goc never reads or writes a `permissions` key anywhere (zero matches in install.py/engine.py); the file is the Claude Code hook-registration manifest that `goc install`/`goc upgrade` merge GOC_CLAUDE_HOOKS entries into and that the plugin-mode cleanup strips them back out of. AGENTS.md's own skills_source table contradicts line 202 by stating plugin mode is the case where upgrade does NOT write GoC entries in that file."
status: done
stage: null
contribution: high
created: "2026-07-26T19:06:59Z"
closed_at: "2026-07-26T19:12:39Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — AGENTS.md no longer calls `.claude/settings.json` a "project-specific permission allow-list"
  - [x] TDD: a guard in `tests/test_guidance_accuracy.py` fails if any guidance surface describes `.claude/settings.json` as a permission allow-list, or claims goc writes a `permissions` key
  - [x] MECHANICAL: the AGENTS.md dogfood-sync paragraph names the file for what it is (the Claude Code hook-registration manifest `goc install`/`goc upgrade` merge `GOC_CLAUDE_HOOKS` entries into, and plugin-mode cleanup strips them from) and says why it is out of the byte-mirror sync (it is a *merge* target, not a mirrored file)
  - [x] PROCESS: `uv run goc validate` passes and the regression suite stays green
worker: {who: "claude[bot]", where: main}
---

# AGENTS.md calls `.claude/settings.json` a per-repo permission allow-list; goc writes hook registrations into it

## Location

`AGENTS.md:201-207`, the closing paragraph of
"### Skill and hook files have two copies — edit the template, sync handles the rest":

```markdown
The `.game-of-cards/` content stubs (project-local deck README,
config) and `.claude/settings.json` (project-specific permission
allow-list) are NOT in the auto-sync — they're meant to be customized
per repo.
```

## What's broken

Two independent errors in one parenthetical.

**1. The file holds no permissions, and goc never writes any.** `goc`
contains zero occurrences of the string `permissions` across both modules
that touch install state:

```
goc/install.py: 0
goc/engine.py: 0
```

This repo's own copy is `{"hooks": {...}}` — three registrations, no
`permissions` key. The only permission grant GoC documents anywhere is the
`Bash(goc:*)` allowance in `Skill(claude-kickoff)`, which the *human* adds;
the engine has never written it.

**2. The file is a goc-managed merge target, not a per-repo file.**
`goc install` merges the `GOC_CLAUDE_HOOKS` event map into it
(`goc/install.py:614`), and the plugin-mode cleanup strips those same
entries back out (`goc/install.py:701`, `:830`). `goc validate` then
enforces registration parity against that map
(`engine.validate_hook_registration`). So ownership is *shared*: the
`hooks` entries whose command matches `GOC_CLAUDE_HOOKS` are goc-owned;
anything else the repo adds is user-owned.

AGENTS.md contradicts itself on exactly this point 36 lines later, in the
`skills_source` table at `AGENTS.md:238`:

> `plugin` | ... `goc upgrade` does not write `.claude/skills/`,
> `.claude/hooks/`, or **GoC entries in `.claude/settings.json`**.

Naming plugin mode as the case where upgrade does *not* write those entries
states plainly that vendored mode *does* — which is irreconcilable with the
earlier framing of the same file as hands-off and "customized per repo".

The "NOT in the auto-sync" half of the sentence is accurate:
`scripts/sync_plugin_assets.py` has no `settings` reference and never
mirrors the file. But the stated *reason* is wrong. It is excluded because
it is a **merge** target — install/upgrade reconcile GoC entries into
whatever the repo already has — not because it is user-owned content like
the six `.game-of-cards/` stubs it is grouped with.

## Empirical evidence

Before the fix, `reproduce.py` exited 1 on check 1 — AGENTS.md:202 carried
the mislabel — while checks 2–4 established the ground truth it contradicted:

```
=== 2. `permissions` occurrences in the engine ===
goc/install.py: 0
goc/engine.py: 0

=== 3. .claude/settings.json contents ===
top-level keys: ['hooks']
has `permissions`: False
registered hook commands: 3
  deck_session_start.py                  in GOC_CLAUDE_HOOKS: True
  deck_prompt_router.py                  in GOC_CLAUDE_HOOKS: True
  pattern_generalization_check.py        in GOC_CLAUDE_HOOKS: True

=== 4. goc/install.py sites that write/strip GoC hook entries ===
goc/install.py:614: for event, command in GOC_CLAUDE_HOOKS.items():
goc/install.py:701: goc_commands = set(GOC_CLAUDE_HOOKS.values())
goc/install.py:830: for cmd in GOC_CLAUDE_HOOKS.values():

events registered by goc: ['SessionStart', 'Stop', 'UserPromptSubmit']
```

After the fix it exits 0: `PASS: AGENTS.md describes .claude/settings.json
accurately`.

The guard was checked against the pre-fix text rather than assumed to bite:
with `AGENTS.md` reverted to `b8f146c3` in a scratch worktree,
`ClaudeSettingsOwnershipAccuracyTest` reports 2 failures (the allow-list
phrase, and the missing hook-registration-manifest paragraph) and 0 errors.

## Why it matters

That paragraph exists to answer one question for a contributor: *which
files may I hand-edit?* It answers wrong for `.claude/settings.json`.

A contributor who trusts it edits the `hooks` block directly — reasonable,
for a file described as per-repo and out of the sync. The next
`goc upgrade` in vendored mode re-merges the GoC registrations over that
work, and `goc validate` reports a hook-registration mismatch against
`GOC_CLAUDE_HOOKS` if the edit renamed or dropped one. The correct
instruction is the same as for the other goc-owned surfaces: change
`GOC_CLAUDE_HOOKS` in `goc/install.py` and let install/upgrade write the
registration.

The mislabel also sends a reader hunting for a permissions allow-list that
has never existed in any released version — and it sits immediately above
the "### `.game-of-cards/` ownership model and `goc upgrade` contract"
table, whose whole subject is per-file ownership and which does not list
`.claude/settings.json` at all.

This is one instance of the shape tracked by
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/):
the claim was never wired to a guard, so it rotted silently while the code
around it stayed correct. The sibling cards
[install-overwrites-malformed-claude-settings-json-instead-of-merging](../install-overwrites-malformed-claude-settings-json-instead-of-merging/)
and
[goc-upgrade-leaves-stale-prior-version-hook-registrations-in-claude-settings](../goc-upgrade-leaves-stale-prior-version-hook-registrations-in-claude-settings/)
audit the merge *behavior*; this card fixes the doc that misdescribes who
owns the file.

## Fix (applied)

`AGENTS.md` — the one paragraph now splits the two exclusions by their real
reasons instead of lumping them together: the `.game-of-cards/` stubs are
**user-owned** (nothing regenerates them), while `.claude/settings.json` is
the Claude Code **hook-registration manifest**, excluded because it is a
*merge* target rather than a mirrored file. It states the shared-ownership
rule explicitly — `hooks` entries matching `GOC_CLAUDE_HOOKS` are goc-owned
and are changed in `goc/install.py`, with `goc validate` enforcing the
parity; any other key the repo adds is the repo's. The final sentence
records that goc writes no `permissions` block and points at
`Skill(claude-kickoff)` for the `Bash(goc:*)` grant, which is a human step.

`tests/test_guidance_accuracy.py` — new `ClaudeSettingsOwnershipAccuracyTest`
with three guards:

1. `test_no_doc_calls_settings_json_a_permission_allow_list` — scans
   `AGENTS.md`, `goc.md` and `CONTRIBUTING.md` (the surfaces that tell a
   reader which files are hand-editable) for "permission allow-list" /
   "allowlist" within 120 characters of `.claude/settings.json`, on
   whitespace-collapsed text so the claim cannot hide behind a line wrap.
2. `test_engine_writes_no_permissions_key` — asserts `goc/install.py` and
   `goc/engine.py` stay free of `permissions`. This pins the premise the
   first guard rests on: if goc ever *does* grow a permissions writer, this
   fails and forces the docs to be revisited in the same change rather than
   letting the old claim quietly become true again.
3. `test_agents_md_names_the_hook_registration_constant` — the corrected
   paragraph must name both `GOC_CLAUDE_HOOKS` and `goc/install.py`, so a
   contributor is sent to the real edit site.

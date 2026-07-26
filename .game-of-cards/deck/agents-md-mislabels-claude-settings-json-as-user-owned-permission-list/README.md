---
title: agents-md-mislabels-claude-settings-json-as-user-owned-permission-list
summary: "AGENTS.md's dogfood-sync section calls `.claude/settings.json` a \"project-specific permission allow-list\" that is \"meant to be customized per repo\", grouping it with the user-owned `.game-of-cards/` content stubs. goc never reads or writes a `permissions` key anywhere (zero matches in install.py/engine.py); the file is the Claude Code hook-registration manifest that `goc install`/`goc upgrade` merge GOC_CLAUDE_HOOKS entries into and that the plugin-mode cleanup strips them back out of. AGENTS.md's own skills_source table contradicts line 202 by stating plugin mode is the case where upgrade does NOT write GoC entries in that file."
status: open
stage: null
contribution: high
created: "2026-07-26T19:06:59Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — AGENTS.md no longer calls `.claude/settings.json` a "project-specific permission allow-list"
  - [ ] TDD: a guard in `tests/test_guidance_accuracy.py` fails if any guidance surface describes `.claude/settings.json` as a permission allow-list, or claims goc writes a `permissions` key
  - [ ] MECHANICAL: the AGENTS.md dogfood-sync paragraph names the file for what it is (the Claude Code hook-registration manifest `goc install`/`goc upgrade` merge `GOC_CLAUDE_HOOKS` entries into, and plugin-mode cleanup strips them from) and says why it is out of the byte-mirror sync (it is a *merge* target, not a mirrored file)
  - [ ] PROCESS: `uv run goc validate` passes and the regression suite stays green
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

`uv run python .game-of-cards/deck/agents-md-mislabels-claude-settings-json-as-user-owned-permission-list/reproduce.py`:

```
=== 1. AGENTS.md claim ===
AGENTS.md:202: `.claude/settings.json` (project-specific permission allow-list)
  ...grouped with the user-owned `.game-of-cards/` content stubs as
  "NOT in the auto-sync — they're meant to be customized per repo".

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

Exit 1.

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

## Fix

Rewrite `AGENTS.md:201-207` so the two exclusions are described by their
real reasons — the `.game-of-cards/` stubs because they are user-owned
content, `.claude/settings.json` because it is a merge target whose GoC
`hooks` entries come from `GOC_CLAUDE_HOOKS` and must be changed there.
Drop "project-specific permission allow-list".

Then add a guard to `tests/test_guidance_accuracy.py` (alongside the
existing `AgentsArchitectureAccuracyTest` / `GocMdPluginReferenceAccuracyTest`
classes) asserting that no guidance surface calls the file a permission
allow-list and that `goc/install.py` + `goc/engine.py` stay free of a
`permissions` key — so the claim and the code cannot drift apart again.

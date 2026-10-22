---
title: agents-md-says-goc-validate-checks-hook-entries-in-claude-settings
summary: "AGENTS.md told contributors to change the goc-owned hook entries in goc/install.py, not in .claude/settings.json, \"and goc validate enforces the parity\". No validate step reads those entries for parity. In a scratch --local-skills install, dropping one registration and repointing another still leaves goc validate at exit 0. The paragraph now says such an edit passes goc validate, and that a vendored-mode goc upgrade re-adds the missing entries but leaves a repointed one behind. A run-it guard checks each of those clauses both ways."
status: done
stage: null
contribution: high
created: "2026-10-05T01:32:49Z"
closed_at: "2026-10-07T04:53:23Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: a reproduce.py runs `goc install --agents claude --local-skills` in a scratch repo, drops the `Stop` registration from `.claude/settings.json`, renames the `SessionStart` script in its command, runs `goc validate`, and fails while `AGENTS.md` still credits `goc validate` with enforcing that parity and validate exits 0 — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] MECHANICAL: `AGENTS.md:248-250` no longer says `goc validate` enforces the parity; it names what does keep the GoC entries in line (the `goc install` / `goc upgrade` merge from `GOC_CLAUDE_HOOKS`), as `tests/test_precommit_hook_reachability.py:74-80` already describes
  - [x] TDD: `tests/test_claude_settings_hook_edit_claims.py` makes the same hand edit in a scratch install, runs `goc validate` and a same-version `goc upgrade`, and checks every clause the rewritten paragraph states both ways; it fires on the pre-fix sentence and on the current one with every observation flipped
  - [x] PROCESS: the closed `agents-md-mislabels-claude-settings-json-as-user-owned-permission-list` gets a post-close pointer to this card; drop the `unverified` tag once reproduce.py lands
worker: {who: "claude[bot]", where: main}
---

# AGENTS.md says goc validate checks the hook entries in `.claude/settings.json`

Confirmed by `reproduce.py` on 2026-10-07 and fixed the same day. Filed
unverified by the 2026-10-05 audit-deck pass.

## Location

- `AGENTS.md`, § "Skill and hook files have two copies", the paragraph that names
  `.claude/settings.json` the hook-registration manifest. Before the fix it said
  the goc-owned `hooks` entries are changed "in `goc/install.py`, not in
  `.claude/settings.json`, and `goc validate` enforces the parity".
- `goc/engine.py`, `validate_hook_registration`: the check that sentence meant.
  It compares `PACKAGE_DIR / "templates" / "hooks"` with `GOC_CLAUDE_HOOKS` and
  never opens a consumer file. `validate_plugin_hook_registration` covers the two
  plugin `hooks.json` files the same way. Those are the "three hand-maintained
  registries" the "Templates ship as package data" section lists, and
  `.claude/settings.json` is not one of them.
- `goc/engine.py`, `validate_plugin_hook_double_fire`: the only validate step
  that reads the file's `hooks` block. It is advisory and asks one question,
  whether GoC hooks are vendored there while the plugin is enabled.
- `goc/install.py`, `_merge_claude_settings`: the thing that does put goc-owned
  entries back. It appends each `GOC_CLAUDE_HOOKS` command missing from its
  event, matching on the exact command string.
- Origin of the sentence: commit `8a89f791` (2026-07-26), which closed
  [agents-md-mislabels-claude-settings-json-as-user-owned-permission-list](../agents-md-mislabels-claude-settings-json-as-user-owned-permission-list/).
  That card's guard, `ClaudeSettingsOwnershipAccuracyTest`, pinned the two names
  the repair added (`GOC_CLAUDE_HOOKS`, `goc/install.py`) but not the validate
  clause in the same parenthetical.

## Evidence

`reproduce.py` runs the card's recipe against this tree. Before the fix it
exited 1:

```
AGENTS.md `.claude/settings.json` paragraph:
  credits `goc validate` with the parity: True  ('`goc validate` enforces')

[1] fresh --local-skills install: goc validate -> exit 0
[2] hand-edit .claude/settings.json
    events before: ['SessionStart', 'Stop', 'UserPromptSubmit']
    events after:  ['SessionStart', 'UserPromptSubmit']
    SessionStart:  ['python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start_RENAMED.py']
[3] goc validate -> exit 0

[context] same-version goc upgrade -> exit 0
    GOC_CLAUDE_HOOKS entries still missing: none
    repointed entry still registered: True

DEFECT PRESENT: goc validate exits 0 on a dropped and a repointed registration, yet AGENTS.md says it enforces the parity.
```

After the fix it exits 0 with `FIXED: goc validate still passes the hand edit,
and AGENTS.md no longer claims it enforces the parity.`

The context lines describe the real behavior the doc now states:

- **The merge is the repair.** A same-version `goc upgrade` in a vendored repo
  re-adds every missing `GOC_CLAUDE_HOOKS` entry. The upgrade's no-op verdict is
  derived from its write plan, and the settings merge is in that plan.
- **The repair is partial.** The repointed command no longer matches any
  `GOC_CLAUDE_HOOKS` value, so it stays registered beside the re-added one and
  fires a missing script on every session start. That is the merge-side gap
  [goc-upgrade-leaves-stale-prior-version-hook-registrations-in-claude-settings](../goc-upgrade-leaves-stale-prior-version-hook-registrations-in-claude-settings/)
  already tracks (open, decision-gated), so this card files no new one.

## Why it mattered

`AGENTS.md` is read cold by every agent working here, and this paragraph answers
"which files may I hand-edit?". A contributor who trusted the sentence believed
a broken registration would fail CI. In fact the hook silently stops firing, or
fires a script that does not exist, while every check stays green. In a vendored
repo those registrations are the whole hook set: session-start reminder, prompt
router, pattern check.

## Fix (applied)

`AGENTS.md`: the parenthetical lost its validate clause. The paragraph now says:

- `.claude/settings.json` is not one of the three hook registries `goc validate`
  covers. It points back at the list instead of restating it, so a hand edit that
  drops or repoints a goc-owned registration passes `goc validate`.
- The merge is what repairs it. A vendored-mode `goc upgrade` re-adds every
  `GOC_CLAUDE_HOOKS` entry the file lacks, even at the same version.
- A repointed entry no longer matches, so it stays behind beside the re-added
  one. The paragraph links the stale-registration card for this.

The fix sketch also mentioned a new vendored-mode check comparing the file with
`GOC_CLAUDE_HOOKS`. It was not built. That would be a feature, and no card asks
for it.

## Guard

The sentence being fixed was itself written by an earlier repair whose guard
pinned only the clause that repair was aimed at. This is the thirteenth
instance's lesson on
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/).
So every clause the rewrite adds is pinned, not just the one this card was
about.

`tests/test_claude_settings_hook_edit_claims.py` (`ClaudeSettingsHookEditClaimsTest`)
makes the hand edit in a scratch `--local-skills` install with an empty `HOME`.
It runs `goc validate` and a same-version `goc upgrade`, then checks the
paragraph against three observations, each both ways:

| Check | The paragraph must... | ...exactly while |
|---|---|---|
| `validate` | say the edit passes `goc validate`, and never credit validate with catching it | validate exits 0 on the edit |
| `upgrade` | say `goc upgrade` re-adds the missing entries | a same-version upgrade restores every `GOC_CLAUDE_HOOKS` entry |
| `repointed` | say the repointed entry stays behind, and link the stale-registration card | the repointed entry survives the upgrade |

Two more tests prove that every check fires. The first feeds in the pre-fix
sentence verbatim with the observations as filed. The second feeds in the
current paragraph with every observation flipped. So if a validate check for
consumer settings lands, or the stale-registration card's fix removes repointed
entries, the build goes red until this paragraph is updated. Checked against the
defect rather than assumed: with `AGENTS.md` at `HEAD` before the fix, the
paragraph check reports four problems across all three checks.

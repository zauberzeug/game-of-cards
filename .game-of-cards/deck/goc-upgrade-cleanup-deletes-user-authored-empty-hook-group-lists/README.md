---
title: goc-upgrade-cleanup-deletes-user-authored-empty-hook-group-lists
summary: "`_strip_goc_settings_entries` (goc/install.py:749) drops every hook *group* whose `hooks: []` ends up empty after filtering — including user-authored placeholder groups the strip pass never touched. Parallel defect to the just-closed event-level case (`goc-upgrade-cleanup-deletes-user-authored-empty-hook-event-lists`), one layer deeper. Reachable through `goc upgrade` switching a repo from vendored to plugin-mode skills."
status: done
stage: null
contribution: medium
created: "2026-05-30T22:29:09Z"
closed_at: "2026-05-30T22:32:17Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (user-authored empty group survives the strip pass)
  - [x] TDD: regression test in tests/ exercises a user-authored `{"matcher": "X", "hooks": []}` placeholder alongside a GoC-managed group (the GoC entry is stripped; the user group survives)
  - [x] MECHANICAL: `_strip_goc_settings_entries` only removes hook groups whose `hooks` list it itself emptied (i.e. it must snapshot pre-existing empty groups before the filter, mirroring the event-level fix)
  - [x] PROCESS: `uv run python -m unittest discover -s tests` passes
  - [x] PROCESS: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `goc upgrade` cleanup deletes user-authored empty hook-group lists

## Location

`goc/install.py:710-750` — inside `_strip_goc_settings_entries`, the
per-group filter and the `if new_hooks:` gate at line 749:

```python
new_groups: list = []
for group in event_value:
    ...
    filtered: list = []
    non_dicts: list = []
    removed_any = False
    for h in group_hooks:
        if not isinstance(h, dict):
            non_dicts.append(h)
            continue
        if h.get("command") in goc_commands:
            removed_any = True
            continue
        filtered.append(h)
    ...
    new_hooks = filtered + non_dicts
    if new_hooks:
        new_groups.append({**group, "hooks": new_hooks})
```

## What's broken

The just-closed sibling card
[`goc-upgrade-cleanup-deletes-user-authored-empty-hook-event-lists`](../goc-upgrade-cleanup-deletes-user-authored-empty-hook-event-lists/)
fixed this defect at the *event* layer: lines 694-697 now snapshot
events whose value was already `[]` before the strip ran, so the
cleanup pass at 755-760 skips them. But the analogous pattern at the
*group* layer was missed.

A user who hand-writes a placeholder group like
`{"matcher": "startup", "hooks": []}` (intending to fill in the hook
commands later) hits this path:

1. The group has `hooks: []` (already empty, no GoC entries to remove).
2. The filter loop iterates `group_hooks = []` zero times. `filtered`
   and `non_dicts` stay empty. `removed_any` stays `False`.
3. `new_hooks = filtered + non_dicts = []`.
4. `if new_hooks:` at line 749 is `False` → the group is **not**
   appended to `new_groups`. The user's placeholder is silently
   dropped.
5. The enclosing `event_value` started with one group and ends with
   zero → `new_groups != event_value` at line 751 → `changed = True`.
6. `hooks[event]` is now `[]`. The event was *not* in `preexisting_empty`
   (it had the placeholder group before strip), so the cleanup pass at
   758-760 deletes the event key.
7. `hooks` is now `{}` → line 762 pops the entire `hooks` key from
   settings.

The fix exists one layer up but not here. The contract
`_strip_goc_settings_entries` claims in its docstring — "Remove
GoC-managed hook entries from .claude/settings.json" — and the
upgrade-prompt contract — "Cleanup removes GoC-managed skill
directories, GoC hook files, and GoC entries in `.claude/settings.json`"
— both say *only GoC-managed entries*. A group with `hooks: []` and
no `command` strings is not GoC-managed by definition.

## Empirical evidence

`reproduce.py` exits non-zero on the buggy code. Output captured
verbatim from `uv run python deck/goc-upgrade-cleanup-deletes-user-authored-empty-hook-group-lists/reproduce.py`:

```
BEFORE: {"hooks": {"SessionStart": [{"matcher": "startup", "hooks": []}]}}
AFTER : {}
ASSERTION FAILED: user-authored group {"matcher": "startup", "hooks": []} was silently destroyed.
```

## Why it matters

Same blast radius as the sibling card. Reachable through `goc upgrade`
when a repo switches from vendored to plugin-mode skills: the upgrade
prompt runs the cleanup pass, which silently deletes user state it has
no business deleting. The user has no warning, no `.bak`, no log
entry — the placeholder group simply disappears.

The reachability path is identical to the closed sibling: a user with
a hand-written `.claude/settings.json` runs `goc upgrade` after editing
`skills_source: plugin`, accepts the cleanup prompt, and finds their
hook scaffolding silently rewritten.

## Fix

Mirror the event-level fix one layer deeper. Before the group filter
runs, snapshot the index of every pre-existing empty group; after
filtering, only drop a group whose `hooks` list this function itself
emptied.

Simplest shape: change the gate at line 749 from `if new_hooks:` to
something like:

```python
if new_hooks or not group_hooks:
    new_groups.append({**group, "hooks": new_hooks})
```

`group_hooks` is the pre-filter list. If it was already empty, the
group is user state; preserve it. Otherwise, if filtering emptied it,
drop it (the existing behavior).

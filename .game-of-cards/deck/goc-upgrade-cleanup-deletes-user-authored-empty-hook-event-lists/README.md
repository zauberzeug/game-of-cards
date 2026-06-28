---
title: goc-upgrade-cleanup-deletes-user-authored-empty-hook-event-lists
summary: "`_strip_goc_settings_entries` (goc/install.py:745-748) unconditionally deletes every empty hook-event list in `.claude/settings.json`, including user-authored placeholders the strip pass never touched. Reachable through `goc upgrade` when switching a repo from vendored to plugin-mode skills (`_strip_claude_vendored_harness`). Violates the cleanup contract that only GoC-managed entries are removed."
status: done
stage: null
contribution: medium
created: "2026-05-30T21:35:51Z"
closed_at: "2026-05-30T21:40:41Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (user-authored empty event list survives the strip pass)
  - [x] TDD: regression test in tests/ exercises an empty user-authored event alongside a GoC-managed event (the GoC entry is stripped; the user entry survives)
  - [x] MECHANICAL: `_strip_goc_settings_entries` only deletes hook events whose final value differs from the pre-strip value (i.e. only events the function itself emptied)
  - [x] PROCESS: `uv run python -m unittest discover -s tests` passes
  - [x] PROCESS: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `goc upgrade` cleanup deletes user-authored empty hook-event lists

## Location

`goc/install.py:745-748` — inside `_strip_goc_settings_entries`:

```python
for event in list(hooks.keys()):
    if isinstance(hooks[event], list) and not hooks[event]:
        del hooks[event]
        changed = True
```

## What's broken

The function's docstring states its purpose unambiguously:

> Remove GoC-managed hook entries from .claude/settings.json.

The filter loop above it (lines 689-743) correctly removes only hook
items whose `command` is in `goc_commands = set(GOC_CLAUDE_HOOKS.values())`,
and rebuilds each event's group list around that. After that filter,
the cleanup pass at 745-748 walks the events again and deletes **every**
empty list, with no regard for whether the function itself emptied it.

Concretely: if the user's `.claude/settings.json` had a placeholder
event `"MyUserEvent": []` they were about to populate, the cleanup pass
deletes it — even though `MyUserEvent` had no GoC entries to begin with.
Once the cleanup also empties the surrounding `hooks` dict (line 750),
the entire `hooks` key disappears from the file.

The contract the cleanup violates is stated directly in the `goc upgrade`
prompt that gates this code path (install.py:1626-1632):

> Cleanup removes GoC-managed skill directories, GoC hook files, and
> GoC entries in .claude/settings.json. Non-GoC skills in .claude/skills/
> are preserved.

User-authored entries should be preserved by parallel construction.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-upgrade-cleanup-deletes-user-authored-empty-hook-event-lists/reproduce.py`:

```
BEFORE: {
  "hooks": {
    "MyUserEvent": []
  }
}
AFTER:  {}
```

Expected `AFTER` value: `{\n  "hooks": {\n    "MyUserEvent": []\n  }\n}` — the
user-authored placeholder must survive a cleanup pass that finds no GoC
entries to remove.

## Why it matters (reachability)

`_strip_goc_settings_entries` is reached through one path:

```
goc upgrade
  → _strip_claude_vendored_harness(target, templates)            # install.py:1635
    → _strip_goc_settings_entries(target / shim.settings_json)   # install.py:803
```

This runs when a repo configured for plugin-mode skills (`skills_source:
plugin` in `.game-of-cards/config.yaml`) still has a leftover
`.claude/skills/` from an earlier vendored install, and the user
confirms the cleanup prompt. A user who keeps placeholder hook events
in `.claude/settings.json` (a common pattern for staging hook
additions) loses them silently — there is no log line naming the
deletion, only the post-write JSON.

The defect is the inverse-direction sibling of the recent strip-pass
shape-guards (`claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard`,
`claude-settings-group-hooks-list-and-items-bypass-nested-isinstance-guards`):
those fixed shape-guarding *during removal*; this is about not
destroying user state *after removal*.

## Fix

Track which events were already empty before the strip pass and skip
those during the cleanup. The narrowest change:

```python
preexisting_empty = {
    event for event, value in hooks.items()
    if isinstance(value, list) and not value
}

# ... existing filter loop ...

for event in list(hooks.keys()):
    if event in preexisting_empty:
        continue
    if isinstance(hooks[event], list) and not hooks[event]:
        del hooks[event]
        changed = True
```

The surrounding `if not hooks: settings.pop("hooks", None)` (line
750-751) should also be guarded by "every key was authored by us" —
trivially satisfied if no preexisting events remain because the user
had only user-authored events.

## Test

`tests/test_install_settings_strip.py` (or add to the existing
strip-test module) should:

1. Build a `.claude/settings.json` containing one GoC-managed event
   (e.g. `SessionStart` with a `goc`-prefixed command) and one
   user-authored empty placeholder event.
2. Call `_strip_goc_settings_entries`.
3. Assert the GoC event is removed and the user placeholder survives
   verbatim.

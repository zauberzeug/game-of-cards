---
title: claude-settings-group-hooks-list-and-items-bypass-nested-isinstance-guards
summary: "The closed sibling `claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard` guarded `hooks` and `hooks[event]` but stopped one layer short. Inside `hooks[event][i]`, the inner `hooks` field and its items are still trusted blindly: a `.claude/settings.json` shaped `{\"hooks\": {\"SessionStart\": [{\"hooks\": \"oops\"}]}}` crashes `_merge_claude_settings` and `_strip_goc_settings_entries` with `AttributeError: 'str' object has no attribute 'get'`; an `int` value at the same key raises `TypeError: 'int' object is not iterable`. Same loader-family root cause, one layer deeper than the closed sibling."
status: open
stage: null
contribution: medium
created: "2026-05-30T18:15:03Z"
closed_at: null
human_gate: none
advances:
  - unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — every layer-4 sub-shape (`group.hooks: "string"`, `group.hooks: 42`, `group.hooks: {"x": 1}`, `group.hooks: [..., "literal", ...]`) surfaces a coherent warning and the function either skips the offending value or coerces it to a safe default; no `AttributeError` or `TypeError` escapes from `_merge_claude_settings` or `_strip_goc_settings_entries`.
  - [ ] TDD: a regression test in `tests/test_install.py` constructs `.claude/settings.json` for each non-list `group["hooks"]` shape AND a list-with-non-dict-item shape, runs both merge and strip, and asserts (a) no exception escapes, (b) the user's original file is preserved verbatim (or backed up) — strip MUST NOT silently rewrite a wrong-shape inner value.
  - [ ] MECHANICAL: `_merge_claude_settings` adds `isinstance(group.get("hooks"), list)` and `isinstance(h, dict)` guards at `install.py:620-624` (the `already = any(...)` block). `_strip_goc_settings_entries` adds the symmetric guards at `install.py:680-684` (the `filtered = [...]` comprehension). Both follow the closed sibling's backup-and-warn / warn-and-skip pattern.
  - [ ] PROCESS: append a note to the meta-fix parent `unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes` body confirming this layer-4 callsite is also fixed under Approach B precedent (counts toward "approach B per-callsite-guard" tally).
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
---

# `.claude/settings.json` group-hooks list and items bypass nested isinstance guards

## Location

- `goc/install.py:620-626` — `_merge_claude_settings`: the `already = any(...)` generator iterates `group.get("hooks", [])` and calls `h.get("command")` without guarding either the list shape or the item shape.
- `goc/install.py:680-684` — `_strip_goc_settings_entries`: the `filtered = [h for h in group.get("hooks", []) if h.get("command") not in goc_commands]` comprehension has the same unguarded shape.

## What's broken

The closed sibling card
[`claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard`](../claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard/)
added two layers of `isinstance` guards to `.claude/settings.json` ingest:

1. Layer 2 — `hooks` is a dict (`install.py:595-605`).
2. Layer 3 — `hooks[event]` is a list (`install.py:608-619` in merge,
   `install.py:667-674` in strip).

But the merge function then walks one layer deeper without guarding:

```python
already = any(
    any(h.get("command") == command for h in group.get("hooks", []))
    for group in event_hooks
    if isinstance(group, dict)
)
```

`group` is checked for `isinstance(group, dict)`, but `group.get("hooks")`
is **not** checked for `isinstance(_, list)`, and the inner `h` is **not**
checked for `isinstance(h, dict)`. So any wrong-shape value at
`hooks[event][i]["hooks"]` crashes:

| Inner shape                                                  | What happens                                                                              |
|--------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| `{"hooks": {"SessionStart": [{"hooks": "oops"}]}}`           | `for h in "oops"` yields chars; `"o".get("command")` → `AttributeError`                   |
| `{"hooks": {"SessionStart": [{"hooks": 42}]}}`               | `for h in 42` → `TypeError: 'int' object is not iterable`                                 |
| `{"hooks": {"SessionStart": [{"hooks": {"x": 1}}]}}`         | dict iteration yields keys (strings); `"x".get("command")` → `AttributeError`             |
| `{"hooks": {"SessionStart": [{"hooks": [{...}, "literal"]}]}}` | reaches `"literal".get("command")` → `AttributeError`                                     |

The strip path has the symmetric shape at `install.py:680`:

```python
filtered = [h for h in group.get("hooks", []) if h.get("command") not in goc_commands]
```

Same iteration, same `.get` call, same four crash shapes.

This is the next layer of the exact same "iterate a scalar / non-list as
if it were a list, call dict methods on each item" defect family that
the sibling meta-fix
[`unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes`](../unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes/)
tracks, and that the recent closed sibling patched at layers 2 and 3.

## Empirical evidence

`uv run python .game-of-cards/deck/claude-settings-group-hooks-list-and-items-bypass-nested-isinstance-guards/reproduce.py`:

```
=== inner_hooks_string: hooks={'SessionStart': [{'hooks': 'oops'}]} ===
  merge: AttributeError: 'str' object has no attribute 'get'
  strip: AttributeError: 'str' object has no attribute 'get'
=== inner_hooks_int: hooks={'SessionStart': [{'hooks': 42}]} ===
  merge: TypeError: 'int' object is not iterable
  strip: TypeError: 'int' object is not iterable
=== inner_hooks_dict: hooks={'SessionStart': [{'hooks': {'x': 1}}]} ===
  merge: AttributeError: 'str' object has no attribute 'get'
  strip: AttributeError: 'str' object has no attribute 'get'
=== inner_hooks_list_with_non_dict_item: hooks={'SessionStart': [{'hooks': [{'command': 'ls'}, 'literal']}]} ===
  merge: AttributeError: 'str' object has no attribute 'get'
  strip: AttributeError: 'str' object has no attribute 'get'
8 / 8 cases crash before any GoC hook entries are merged or stripped.
```

## Why it matters

**Reachability.** `.claude/settings.json` is a user-editable file.
Claude Code documents the `hooks` block as
`{"hooks": {"<EventName>": [{"hooks": [{"type": "command", "command": "..."}]}]}}`
(nested four levels). A user typing or scripting that structure by hand
can plausibly produce any of the wrong-inner shapes above — a single
`"command": "..."` typed at the wrong indent level becomes a string at
`group["hooks"]`; a dict key collision drops a stray scalar in. The
recent closed sibling fixed the symptom at layers 2 and 3 but the
crash surface at layer 4 is the same shape, same function pair, same
user-editable file.

Without the guard, the user sees a raw Python traceback from `goc
install` (and `goc install --strip` / the upgrade path) with no
indication of which field is malformed. Worse, `_strip_goc_settings_entries`
runs before the merge — the crash from strip can wedge a repo where
re-installing requires hand-editing `.claude/settings.json` first.

## Fix

Mirror the closed sibling's backup-and-warn / warn-and-skip pattern
one layer deeper. In `_merge_claude_settings` (around line 620):

```python
for event, command in GOC_CLAUDE_HOOKS.items():
    event_hooks = hooks.setdefault(event, [])
    # ... existing layer-3 guard ...
    new_event_hooks = []
    for group in event_hooks:
        if not isinstance(group, dict):
            new_event_hooks.append(group)
            continue
        group_hooks = group.get("hooks", [])
        if not isinstance(group_hooks, list):
            backup = _ensure_backup()
            print(f"  warning: {settings_path} hooks.{event}[].hooks is "
                  f"{type(group_hooks).__name__} (expected list); backed it "
                  f"up to {backup.name} and reset to []. ...", file=sys.stderr)
            group["hooks"] = []
            group_hooks = group["hooks"]
        # filter non-dict items defensively
        if any(not isinstance(h, dict) for h in group_hooks):
            backup = _ensure_backup()
            print(f"  warning: {settings_path} hooks.{event}[].hooks contains "
                  f"non-object items; backed it up to {backup.name} ...",
                  file=sys.stderr)
        new_event_hooks.append(group)
    # rebuild `already` over the now-safe shape
    already = any(
        any(h.get("command") == command for h in group.get("hooks", []) if isinstance(h, dict))
        for group in new_event_hooks
        if isinstance(group, dict) and isinstance(group.get("hooks"), list)
    )
    if not already:
        event_hooks.append({"hooks": [{"type": "command", "command": command}]})
```

And the symmetric pair in `_strip_goc_settings_entries` around line 680:

```python
group_hooks = group.get("hooks", [])
if not isinstance(group_hooks, list):
    print(f"  warning: {settings_path} hooks.{event}[].hooks is "
          f"{type(group_hooks).__name__} (expected list); leaving it "
          f"untouched ...", file=sys.stderr)
    new_groups.append(group)
    continue
filtered = [
    h for h in group_hooks
    if isinstance(h, dict) and h.get("command") not in goc_commands
]
# preserve non-dict items verbatim (don't silently char-explode)
non_dicts = [h for h in group_hooks if not isinstance(h, dict)]
if non_dicts:
    print(f"  warning: {settings_path} hooks.{event}[].hooks contains "
          f"non-object items; leaving them untouched", file=sys.stderr)
    filtered = filtered + non_dicts
# ...
```

The shape mirrors the closed sibling exactly. `_ensure_backup` already
exists from the closed sibling; no new infrastructure is needed.

## Cross-references

- [`claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard`](../claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard/) — the closed sibling at layers 2 and 3.
- [`claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror`](../claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror/) — the closed top-level sibling.
- [`unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes`](../unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes/) — the meta-fix parent this card advances.

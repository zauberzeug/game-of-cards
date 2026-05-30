---
title: claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard
summary: "The closed sibling `claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror` only guarded the top-level shape of `.claude/settings.json`. The nested `hooks` field and the per-event `hooks[event]` list are still trusted blindly. A user-edited `{\"hooks\": []}` crashes `goc install` with `AttributeError: 'list' object has no attribute 'setdefault'`; a `{\"hooks\": {\"SessionStart\": \"oops\"}}` crashes merge or — worse — silently rewrites the file as `{\"SessionStart\": [\"o\",\"o\",\"p\",\"s\"]}` on `goc install --strip`. Same loader-family root cause, one layer deeper."
status: active
stage: null
contribution: medium
created: "2026-05-30T17:59:55Z"
closed_at: null
human_gate: none
advances:
  - unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — all three sub-shapes (`hooks: []`, `hooks: null`, `hooks.<event>: "string"`) now surface a coherent warning and either skip the offending file or coerce it to a safe default, instead of raising `AttributeError` or silently char-exploding a string into a list.
  - [ ] TDD: a regression test in `tests/` constructs a `.claude/settings.json` for each non-dict nested shape and asserts (a) no `AttributeError` escapes, (b) the user's original file is preserved verbatim (or backed up) — strip MUST NOT rewrite a wrong-shape event value into a list of characters.
  - [ ] MECHANICAL: `_merge_claude_settings` guards `hooks` (line 586) and `hooks[event]` (line 588) for `isinstance(_, dict)` / `isinstance(_, list)` respectively, mirroring the closed sibling's backup-and-warn pattern at the top level. `_strip_goc_settings_entries` adds the symmetric guards at lines 623 and 627.
  - [ ] PROCESS: append a note to the meta-fix parent `unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes` body confirming this nested-callsite layer is also fixed (and counts toward the meta-fix's "approach B per-callsite-guard" tally if/when Approach A consolidation is reconsidered).
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# `.claude/settings.json` nested `hooks` shapes bypass the top-level isinstance guard

## Location

- `goc/install.py:586` — `_merge_claude_settings`: `hooks = settings.setdefault("hooks", {})`
- `goc/install.py:588` — `_merge_claude_settings`: `event_hooks: list = hooks.setdefault(event, [])`
- `goc/install.py:595` — `_merge_claude_settings`: `event_hooks.append({...})`
- `goc/install.py:623` — `_strip_goc_settings_entries`: `hooks = settings.get("hooks", {})`
- `goc/install.py:625` — `_strip_goc_settings_entries`: `for event in list(hooks.keys()):`
- `goc/install.py:627` — `_strip_goc_settings_entries`: `for group in hooks[event]:`

## What's broken

The closed sibling card
[`claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror`](../claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror/)
added a top-level `isinstance(settings, dict)` guard at `install.py:576`
and `:613`:

```python
if not isinstance(settings, dict):
    backup = _backup_unparseable_settings(settings_path, original)
    print(f"  warning: {settings_path} is valid JSON but not an object ...", file=sys.stderr)
    settings = {}
```

But the nested layer is still trusted blindly. Immediately after the
top-level guard, the merge path does:

```python
hooks = settings.setdefault("hooks", {})         # install.py:586
for event, command in GOC_CLAUDE_HOOKS.items():
    event_hooks: list = hooks.setdefault(event, [])  # :588
    already = any(...)
    if not already:
        event_hooks.append({"hooks": [{"type": "command", "command": command}]})  # :595
```

`setdefault` only sets when the key is absent; it does not coerce a
present-but-wrong-shape value. So:

| Input shape                                          | What happens                                                                  |
|------------------------------------------------------|-------------------------------------------------------------------------------|
| `{"hooks": []}` or `{"hooks": null}` or `{"hooks": "oops"}` | `hooks.setdefault(event, [])` raises `AttributeError` — install fails noisily |
| `{"hooks": {"SessionStart": "oops"}}`                | `event_hooks.append(...)` raises `AttributeError: 'str' object has no attribute 'append'` |
| `{"hooks": {"SessionStart": {"x": 1}}}`              | `event_hooks.append(...)` raises `AttributeError: 'dict' object has no attribute 'append'` |

The strip path has a different but symmetric failure. `_strip_goc_settings_entries`:

```python
hooks = settings.get("hooks", {})                # install.py:623
for event in list(hooks.keys()):                  # :625
    new_groups: list = []
    for group in hooks[event]:                    # :627
        if not isinstance(group, dict):
            new_groups.append(group)
            continue
        filtered = [...]
        ...
    ...
    hooks[event] = new_groups                     # :638
```

If `hooks` is not a dict, `list(hooks.keys())` raises `AttributeError`.
And if `hooks[event]` is a string (e.g. `"oops"`), the inner `for group
in hooks[event]:` iterates the string **character-by-character**. The
isinstance check on `group` filters each char as "not a dict" and
appends it to `new_groups` — so `"oops"` becomes `["o", "o", "p", "s"]`
and is written back to disk. **The user's settings.json is silently
rewritten into a corrupted shape with no warning.**

This is exactly the "iterate a scalar as if it were a list" defect
shape the sibling meta-fix
[`bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/)
tracks for YAML frontmatter — now surfaced inside JSON settings.

## Empirical evidence

`uv run python .game-of-cards/deck/claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard/reproduce.py`:

```
shape #1: hooks is a list
  merge result: CRASH — AttributeError: 'list' object has no attribute 'setdefault'

shape #2: hooks.SessionStart is a string (merge path)
  merge result: CRASH — AttributeError: 'str' object has no attribute 'append'

shape #3: hooks.SessionStart is a string (strip path) — SILENT CORRUPTION
  strip result: OK (no exception)
  file before strip: {"hooks": {"SessionStart": "oops"}}
  file after strip:  {
    "hooks": {
      "SessionStart": [
        "o",
        "o",
        "p",
        "s"
      ]
    }
  }
  --> the user's "oops" string was char-exploded into a list with no warning
```

## Why it matters — reachability

`.claude/settings.json` is a user-editable file owned by the Claude
Code host, not by GoC. Any of the following produces a wrong-shape
nested value that reaches the unguarded callsites:

- User runs an unrelated tool that writes `{"hooks": []}` as a
  placeholder "no hooks configured" sentinel before `goc install`
  layers GoC entries on top.
- User hand-edits the file with a misremembered shape (mapping vs
  list of events) — easy to do; the file has no schema reference
  shipped alongside.
- A previous corrupted strip pass left `hooks.<event>` as a
  char-list `["o","o","p","s"]`; the next merge pass then iterates
  the char-list, treats each single-char string as a "not a dict"
  group, and `event_hooks.append(...)` succeeds — but now the file
  permanently mixes char-strings with the new GoC entry dict. The
  corruption is sticky.

The strip-side silent corruption is the worst symptom: there's no
traceback, no warning, no backup. The user's intended value (which
might be a typo, but might also be a deliberate non-list placeholder
they planned to fix later) is destroyed.

## Fix proposal

Mirror the closed-sibling backup-and-warn shape at each nested
callsite. Two-line guards each, no decision required:

```python
# install.py:586 (_merge_claude_settings, after top-level guard)
hooks = settings.setdefault("hooks", {})
if not isinstance(hooks, dict):
    backup = _backup_unparseable_settings(settings_path, original)
    print(
        f"  warning: {settings_path} has a non-object `hooks` field "
        f"(got {type(hooks).__name__}); backed it up to {backup.name} "
        f"before writing GoC hooks. Merge your keys back in by hand.",
        file=sys.stderr,
    )
    settings = {"hooks": {}}
    hooks = settings["hooks"]

for event, command in GOC_CLAUDE_HOOKS.items():
    event_hooks = hooks.setdefault(event, [])
    if not isinstance(event_hooks, list):
        # warn and reset this event's list; user's pre-existing value
        # is preserved in the backup taken above (if applicable).
        print(
            f"  warning: {settings_path} hooks.{event} is "
            f"{type(event_hooks).__name__} (expected list); resetting to [].",
            file=sys.stderr,
        )
        hooks[event] = []
        event_hooks = hooks[event]
    ...
```

And symmetric guards at `:623` and `:627` in
`_strip_goc_settings_entries`. The strip path is the higher-stakes
fix: it should refuse to write at all when nested shapes are wrong,
since strip's contract is "remove GoC entries cleanly" — silently
char-exploding a string violates that contract.

The fix is mechanical and follows the closed sibling's pattern. No
decision is required between alternatives — the meta-fix parent
[`unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes`](../unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes/)
still owns the broader Approach A vs B question (consolidate through
a shared helper, or keep applying per-callsite guards). This card
applies Approach B by default, consistent with the closed sibling
precedent; if Approach A wins the meta-fix decision later, these
guards convert cleanly into helper calls.

## Cross-references

- [`claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror`](../claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror/) — the closed parent that fixed the top-level shape only.
- [`unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes`](../unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes/) — meta-fix parent; this card is one more leaf-instance under it.
- [`bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/) — the "iterate a string char-by-char as if it were a list" sibling meta-fix family, now reproduced inside JSON settings as the strip-path silent corruption.

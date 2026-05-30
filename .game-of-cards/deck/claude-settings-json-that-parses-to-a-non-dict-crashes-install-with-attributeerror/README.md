---
title: claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror
summary: "When `.claude/settings.json` is valid JSON but parses to a non-dict (`null`, a list, a bare string/number), both `_merge_claude_settings` and `_strip_goc_settings_entries` call `dict` methods on the parsed value (`.setdefault`, `.get`) and crash with a raw `AttributeError` traceback. Same point-away-from-the-problem failure the closed sibling `frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror` eliminated for the YAML frontmatter parser, in a code path the closed `install-overwrites-malformed-claude-settings-json-instead-of-merging` fix only covered for `JSONDecodeError`."
status: done
stage: null
contribution: medium
created: "2026-05-30T17:14:06Z"
closed_at: "2026-05-30T17:19:48Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — every non-mapping JSON shape (`null`, top-level list, bare string, bare number) in `.claude/settings.json` is handled coherently by `_merge_claude_settings` and `_strip_goc_settings_entries` instead of raising `AttributeError`.
  - [x] TDD: when `.claude/settings.json` parses to a non-dict, the original bytes are preserved (a timestamped `.bak` sibling is written by `_merge_claude_settings`, matching the existing malformed-JSON branch) and a warning is printed to stderr naming the backup.
  - [x] TDD: a regression test in `tests/` covers each non-dict shape (`null`, `[]`, `"string"`, `42`) against both `_merge_claude_settings` and `_strip_goc_settings_entries` and asserts no `AttributeError` escapes.
  - [x] MECHANICAL: the non-dict guard lives in or just after the `json.loads` block in both `_merge_claude_settings` (`goc/install.py:567`) and `_strip_goc_settings_entries` (`goc/install.py:596`); behavior matches the existing `JSONDecodeError` path (backup + warn for the merge function, warn + early return for the strip function).
  - [x] EMPIRICAL: `goc install` and `goc upgrade --agents claude` both complete cleanly against a repo whose `.claude/settings.json` is `null`, with the original bytes preserved in a `.bak` sibling.
worker: {who: "claude[bot]", where: main}
---

# `.claude/settings.json` that parses to a non-dict crashes install with `AttributeError`

## Location

`goc/install.py:567-577` — `_merge_claude_settings`, the `json.loads`
block at line 567 and the unconditional `settings.setdefault(...)` at
line 577.

`goc/install.py:596-606` — `_strip_goc_settings_entries`, the
`json.loads` at line 596 and the `settings.get("hooks", {})` at line
606.

## What's broken

`_merge_claude_settings` parses the existing settings file and then
calls dict methods on the parsed value, assuming a mapping:

```python
settings: dict = {}
if settings_path.exists():
    original = settings_path.read_text()
    try:
        settings = json.loads(original)
    except json.JSONDecodeError as exc:
        backup = _backup_unparseable_settings(settings_path, original)
        print(
            f"  warning: {settings_path} is not valid JSON ({exc}); "
            f"backed it up to {backup.name} before writing GoC hooks. "
            f"Merge your keys back in by hand.",
            file=sys.stderr,
        )

hooks = settings.setdefault("hooks", {})   # <-- crashes if settings is not a dict
```

The annotation `settings: dict = {}` is wishful thinking. `json.loads`
happily returns `None`, `list`, `str`, `int`, `float`, or `bool` when
the document is valid JSON of a non-object type — and any of those
makes `settings.setdefault(...)` raise a raw
`AttributeError: 'NoneType' object has no attribute 'setdefault'`
(or `'list' object has no attribute ...`, etc.) with a bare Python
traceback. The closed predecessor card
[`install-overwrites-malformed-claude-settings-json-instead-of-merging`](../install-overwrites-malformed-claude-settings-json-instead-of-merging/)
fixed the `JSONDecodeError` path but the *valid-JSON, wrong-shape*
path was never covered.

`_strip_goc_settings_entries` has the same shape one function below:

```python
try:
    settings = json.loads(settings_path.read_text())
except json.JSONDecodeError as exc:
    print(...)
    return

goc_commands = set(GOC_CLAUDE_HOOKS.values())
hooks = settings.get("hooks", {})   # <-- crashes if settings is not a dict
```

Same defect, same input — `goc upgrade` in plugin-mode cleanup path
crashes with `AttributeError: 'NoneType' object has no attribute 'get'`.

This is the same point-away-from-the-problem failure the closed
sibling
[`frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror`](../frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror/)
eliminated in `parse_frontmatter` (YAML that parses to a non-mapping
crashed `load_card` with `AttributeError` on `fm.get(...)`). Same root
cause: loader returns "valid but wrong shape", caller blindly calls a
dict method.

## Empirical evidence

```text
$ python3 /tmp/reproof/repro.py
--- input: settings.json is the JSON document `null` (valid JSON, not a dict)
merge CRASHED: AttributeError: 'NoneType' object has no attribute 'setdefault'
--- input: settings.json is the JSON document `[]` (valid JSON, list not dict)
merge CRASHED: AttributeError: 'list' object has no attribute 'setdefault'
--- strip on settings.json = `null`
strip CRASHED: AttributeError: 'NoneType' object has no attribute 'get'
```

See `reproduce.py` in this directory; run via
`uv run python .game-of-cards/deck/claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror/reproduce.py`.

## Why it matters

`.claude/settings.json` is a user-editable file. The realistic
reachability paths:

- The user clears settings by writing the literal `null` (a one-token
  reset, valid JSON). Next `goc install` or `goc upgrade --agents
  claude` crashes mid-flight.
- An external tool writes `[]` as a "no settings yet" sentinel
  (legitimate JSON, just the wrong shape). Same crash.
- A hand-edit accidentally wraps the top-level object in brackets
  (`[{...}]`) before saving. Same crash.

The closed predecessor card
[`install-overwrites-malformed-claude-settings-json-instead-of-merging`](../install-overwrites-malformed-claude-settings-json-instead-of-merging/)
explicitly required `goc install` / `goc upgrade` to handle a settings
file in any wrong shape gracefully (backup + warn, not silent
data loss). Its DoD wording — "the failure is surfaced (warning
printed), not silently swallowed" — implicitly covered this case too,
but the implementation only routed `JSONDecodeError` through
`_backup_unparseable_settings`. The non-dict-but-valid path is a tight
gap in that fix.

User-visible symptom: `goc install` or `goc upgrade --agents claude`
exits non-zero with a Python traceback pointing at `install.py:577`
instead of the contracted backup-and-warn behavior. No path forward
short of deleting or rewriting the settings file by hand.

## Fix

Both functions need a "valid-JSON but non-dict" guard alongside the
existing `JSONDecodeError` branch. The minimal shape:

```python
# in _merge_claude_settings, after the existing try/except:
if not isinstance(settings, dict):
    backup = _backup_unparseable_settings(settings_path, original)
    print(
        f"  warning: {settings_path} is valid JSON but not an object "
        f"(got {type(settings).__name__}); backed it up to {backup.name} "
        f"before writing GoC hooks. Merge your keys back in by hand.",
        file=sys.stderr,
    )
    settings = {}
```

```python
# in _strip_goc_settings_entries, after the existing try/except:
if not isinstance(settings, dict):
    print(
        f"  warning: {settings_path} is valid JSON but not an object "
        f"(got {type(settings).__name__}); leaving it untouched "
        f"(GoC hook entries not removed).",
        file=sys.stderr,
    )
    return
```

This mirrors the existing `JSONDecodeError` paths exactly (backup +
warn for merge, early return + warn for strip). No new helper needed;
the backup function and the warning shape already exist.

Alternative considered: lift the non-dict check into a shared loader
helper that both functions call. Rejected as overkill for two
call-sites — duplicating the four-line guard reads more clearly than
threading a helper. If a third call-site appears, fold it into a
helper at that point.

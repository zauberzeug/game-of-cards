---
title: install-overwrites-malformed-claude-settings-json-instead-of-merging
summary: "`_merge_claude_settings` swallows a JSONDecodeError on an existing `.claude/settings.json` and writes a fresh file with GoC hooks only — silently destroying the user's `permissions.allow`, `env`, and any other keys. Contradicts the function's own docstring contract to merge without removing unrelated keys."
status: active
stage: null
contribution: high
created: "2026-05-27T09:49:10Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits non-zero (the user's `permissions`/`env` keys survive a `goc install`/`upgrade` over a malformed settings.json).
  - [ ] TDD: when the existing settings.json is unparseable, the original bytes are preserved (a timestamped `.bak` sibling is written) and the failure is surfaced (warning printed), not silently swallowed.
  - [ ] MECHANICAL: the `except json.JSONDecodeError: pass` branch at `install.py:558-559` no longer falls through to an unconditional overwrite.
  - [ ] PROCESS: behavior verified for both `goc install` and `goc upgrade --agents claude` entry points (both call `_merge_claude_settings`).
worker: {who: "claude[bot]", where: main}
---

# install overwrites a malformed `.claude/settings.json` instead of merging

## Location

`goc/install.py:547-572` — `_merge_claude_settings`, specifically the
parse-failure branch at lines 557-559 and the unconditional rewrite at line 572.

## What's broken

The merge reads the existing settings, and on a parse failure silently
discards it:

```python
settings: dict = {}
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        pass          # <-- swallows the error; `settings` stays {}
...
settings_path.write_text(json.dumps(settings, indent=2) + "\n")  # <-- overwrites with hooks only
```

So when a user's `.claude/settings.json` is present but malformed (a trailing
comma, a stray comment, a hand-edit typo), `settings` is reset to `{}`, GoC
adds only its three hook registrations, and the file is rewritten — wiping the
user's `permissions.allow`, `env`, and every other key. No backup, no warning.

This directly contradicts the function's own docstring:

```
Adds GoC-managed hook entries under each event type without removing
unrelated keys or hooks that belong to the user.
```

and the closure contract of the done card
[`claude-install-registers-runtime-hooks`](../claude-install-registers-runtime-hooks/),
which required `goc install`/`upgrade` to "merge `.claude/settings.json`
rather than overwriting unrelated user settings." That card delivered the
merge for the *valid-JSON* path; the *malformed-JSON* path was never covered
and still overwrites.

## Empirical evidence

`uv run python deck/install-overwrites-malformed-claude-settings-json-instead-of-merging/reproduce.py`:

```
BEFORE (user's malformed file):
{
  "permissions": {
    "allow": ["Bash(ls:*)", "Bash(uv run goc:*)"]
  },
  "env": {"FOO": "bar"},
}

AFTER _merge_claude_settings:
{
  "hooks": { ...only GoC's three hooks... } }

DEFECT REPRODUCED: silently lost user keys: permissions.allow, env
The malformed file was overwritten with GoC hooks only; no backup written.
```

## Why it matters

`permissions.allow` is exactly the surface GoC itself instructs users to
hand-edit (the Bash allow-list that lets `goc` run without prompts), so a
malformed settings.json is a realistic state — a single trailing-comma typo
is enough. Running `goc install` or `goc upgrade` against that repo silently
deletes the user's permission grants and env config. The data is unrecoverable
(no backup is written) and the loss is silent (no warning), so the user only
discovers it when something stops working.

## Fix

In `_merge_claude_settings`, the parse-failure branch must not fall through to
a destructive overwrite. Recommended (non-destructive, doesn't abort the
install flow): before resetting `settings = {}`, write the original bytes to a
timestamped backup sibling (e.g. `settings.json.bak` or
`settings.json.<ts>.bak`) and print a warning naming the backup path, so the
user's data is recoverable and the loss is visible. The same guard applies to
`_strip_goc_settings_entries` (`install.py:579-582`), which also swallows
`JSONDecodeError` — though that path only declines to edit (returns early)
rather than overwriting, so it is lower-risk; confirm it stays non-destructive.

Alternative considered: abort the install/upgrade with a clear error telling
the user to fix or move aside the malformed file. Rejected as the primary fix
because it breaks non-interactive install flows; the backup-and-warn approach
preserves data without halting setup.

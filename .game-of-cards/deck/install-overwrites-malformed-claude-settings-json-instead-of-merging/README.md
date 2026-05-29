---
title: install-overwrites-malformed-claude-settings-json-instead-of-merging
summary: "`_merge_claude_settings` swallows a JSONDecodeError on an existing `.claude/settings.json` and writes a fresh file with GoC hooks only — silently destroying the user's `permissions.allow`, `env`, and any other keys. Contradicts the function's own docstring contract to merge without removing unrelated keys."
status: done
stage: null
contribution: high
created: "2026-05-27T09:49:10Z"
closed_at: "2026-05-27T09:56:55Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits non-zero (the user's `permissions`/`env` keys survive a `goc install`/`upgrade` over a malformed settings.json).
  - [x] TDD: when the existing settings.json is unparseable, the original bytes are preserved (a timestamped `.bak` sibling is written) and the failure is surfaced (warning printed), not silently swallowed.
  - [x] MECHANICAL: the `except json.JSONDecodeError: pass` branch at `install.py:558-559` no longer falls through to an unconditional overwrite.
  - [x] PROCESS: behavior verified for both `goc install` and `goc upgrade --agents claude` entry points (both call `_merge_claude_settings`).
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

## Empirical evidence (resolved)

`uv run python deck/install-overwrites-malformed-claude-settings-json-instead-of-merging/reproduce.py`
now exits 1 — the user's bytes survive:

```
  warning: .../settings.json is not valid JSON (...); backed it up to
  settings.json.<ts>.bak before writing GoC hooks. Merge your keys back in by hand.

AFTER _merge_claude_settings:
{
  "hooks": { ...GoC's three hooks... } }

Data preserved — original bytes backed up to settings.json.<ts>.bak.
```

Before the fix the same script exited 0: the malformed file was overwritten
with GoC hooks only and no backup was written, silently losing
`permissions.allow` and `env`.

## Why it matters

`permissions.allow` is exactly the surface GoC itself instructs users to
hand-edit (the Bash allow-list that lets `goc` run without prompts), so a
malformed settings.json is a realistic state — a single trailing-comma typo
is enough. Running `goc install` or `goc upgrade` against that repo silently
deletes the user's permission grants and env config. The data is unrecoverable
(no backup is written) and the loss is silent (no warning), so the user only
discovers it when something stops working.

## Fix (applied)

`_merge_claude_settings` now routes the parse-failure branch through
`_backup_unparseable_settings`: it writes the original bytes to a timestamped
sibling (`settings.json.<UTC-ts>.bak`) and prints a warning to stderr naming
the backup before falling back to `settings = {}`. The user's data is
recoverable and the loss is visible; the install flow still completes
(non-interactive installs don't abort). The valid-JSON merge path is
unchanged — user keys are merged in place with no backup.

`_strip_goc_settings_entries` already declined to edit on a parse failure
(returns early, non-destructive); it now also prints a warning so the skip
isn't silent.

Alternative considered: abort the install/upgrade with a clear error telling
the user to fix or move aside the malformed file. Rejected because it breaks
non-interactive install flows; backup-and-warn preserves data without halting
setup.

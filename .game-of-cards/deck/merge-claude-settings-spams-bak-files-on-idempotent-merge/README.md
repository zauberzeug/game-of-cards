---
title: merge-claude-settings-spams-bak-files-on-idempotent-merge
status: done
stage: null
contribution: medium
created: "2026-06-24T02:02:28Z"
closed_at: "2026-06-24T02:07:29Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: a new test in tests/test_install.py merges a settings file that already carries every GoC hook AND contains a non-object hook item, twice; asserts zero `settings.json.*.bak` siblings are created and the file is byte-for-byte unchanged
  - [x] TDD: a companion assertion confirms the non-object-items warning/backup STILL fires when GoC must rewrite the file (a hook is missing), so the safety copy is preserved on a real mutation
  - [x] MECHANICAL: `_merge_claude_settings` no longer calls `_ensure_backup()` from the no-op non-object-items branch; the backup is gated on an actual write
  - [x] PROCESS: full regression suite green (`uv run python -m unittest discover -s tests`)
worker: {who: "claude[bot]", where: main}
---

# merge-claude-settings-spams-bak-files-on-idempotent-merge

## Summary

`_merge_claude_settings` writes a fresh timestamped `settings.json.<UTC>.bak`
sibling and prints a warning on *every* run when the user's
`.claude/settings.json` contains a non-object item inside a
`hooks.<event>[].hooks` list — even when the merge changes nothing.
The recent fix `merge-claude-settings-rewrites-settings-json-on-idempotent-merge`
gated the final `write_text` on a `changed` flag but left this
no-op branch's backup side effect ungated, so repeated `goc upgrade`
runs accumulate dead `.bak` files in the user's `.claude/` directory.

## Location

`goc/install.py:641-648` — the non-object-items branch inside
`_merge_claude_settings`.

## What's broken

The branch backs up and warns but performs no mutation, and never sets
`changed = True`:

```python
elif any(not isinstance(h, dict) for h in group_hooks):
    backup = _ensure_backup()          # fires every run; not gated on `changed`
    print(
        f"  warning: {settings_path} hooks.{event}[].hooks contains "
        f"non-object items; backed it up to {backup.name}. The "
        f"non-object items are preserved verbatim.",
        file=sys.stderr,
    )
```

`_ensure_backup()` → `_backup_unparseable_settings` (`install.py:548`)
writes a new `settings.json.<ts>.bak` on first call per merge. Because
this branch makes no change, an idempotent merge (every GoC hook
already present) leaves `changed = False`, the file is correctly NOT
rewritten at line 663 — yet a `.bak` was already spawned during the
scan, and the warning printed.

Contrast the four *mutating* malformed-shape branches (non-dict root,
non-object `hooks`, non-list `event_hooks`, non-list `group_hooks` at
lines 586/598/612/630): each backs up AND sets `changed = True`, so its
backup is justified by an actual rewrite. Only the non-object-*items*
branch backs up without changing — the contract intent stated in the
line 659-662 comment ("only rewrite the user-owned file when GoC
actually changed something") is violated for the backup, even though
the write itself was correctly guarded.

## Why it matters

Reachability: `goc upgrade` (or a re-run `goc install`) in
vendored / `--local-skills` Claude mode →
`_sync_agent_harness(..., "claude")` → `_merge_claude_settings`.
A user `.claude/settings.json` whose `hooks.<event>[].hooks` list holds
any non-dict element — a plausible hand-edit (a stray string, a
commented-out placeholder marshalled as a literal) — triggers it. Every
subsequent upgrade leaves a new dead `.bak`. The directory accrues
`settings.json.20260101T....bak`, `...20260102T....bak`, … with no
change ever made — the exact "idempotent operations must be quiet"
contract the sibling card established, missed in one branch.

## Empirical evidence

See `reproduce.py`. On a settings file that already carries every GoC
hook plus one non-object item, repeated merges each create a `.bak`
sibling and print the warning while `settings.json` stays byte-for-byte
identical.

Before the fix (the `.bak` collapses to one file only because all runs
share the same UTC-second timestamp; the warning fires once per run):

```
  warning: .../settings.json hooks.SessionStart[].hooks contains non-object items; backed it up to settings.json.<ts>.bak. The non-object items are preserved verbatim.
  warning: .../settings.json hooks.SessionStart[].hooks contains non-object items; backed it up to settings.json.<ts>.bak. The non-object items are preserved verbatim.
  warning: .../settings.json hooks.SessionStart[].hooks contains non-object items; backed it up to settings.json.<ts>.bak. The non-object items are preserved verbatim.
distinct .bak files created across 3 idempotent merges: 1
settings.json byte-for-byte unchanged:                  True

FAIL: an idempotent merge created backup file(s) and warned;
      expected 0 backups when GoC changes nothing.
```

After the fix:

```
distinct .bak files created across 3 idempotent merges: 0
settings.json byte-for-byte unchanged:                  True

PASS: no backup created on a no-op merge.
```

## Fix

Defer the non-object-items backup+warning until GoC is actually going
to rewrite the file. Collect the affected events during the scan, then
in the existing `if changed:` block emit the backup and warning before
the `write_text`. `_ensure_backup` writes the pristine `original`
bytes captured up front, so deferring it to the write point preserves
the same safety copy on a real mutation while making a no-op merge
silent (zero `.bak`, no warning).

---
title: merge-claude-settings-rewrites-settings-json-on-idempotent-merge
status: active
stage: null
contribution: medium
created: "2026-06-23T20:01:33Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
summary: "`_merge_claude_settings` writes `.claude/settings.json` unconditionally, even when every GoC hook is already registered. The no-op re-serialisation reflows the user's chosen indentation and re-orders top-level keys — a spurious diff in a checked-in user file on every idempotent `goc install`/`goc upgrade`. The sibling `_strip_goc_settings_entries` already threads a `changed` flag and guards its write; mirror that here."
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (idempotent merge leaves the user file byte-identical)
  - [ ] TDD: regression test asserts a no-op re-merge does not rewrite settings.json, AND a merge that genuinely adds a missing hook still writes
  - [ ] MECHANICAL: `_merge_claude_settings` guards its `write_text` with a `changed` flag, mirroring `_strip_goc_settings_entries`
  - [ ] PROCESS: full suite green (`uv run python -m unittest discover -s tests`) and `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# merge-claude-settings-rewrites-settings-json-on-idempotent-merge

## Location

`goc/install.py:653` — the final `settings_path.write_text(...)` of
`_merge_claude_settings` (function spans lines 556–653).

## What's broken

`_merge_claude_settings` computes per-hook idempotency (`already`) but
never tracks whether *any* change actually occurred. It writes
unconditionally:

```python
        already = any(
            isinstance(h, dict) and h.get("command") == command
            for group in event_hooks
            if isinstance(group, dict) and isinstance(group.get("hooks"), list)
            for h in group["hooks"]
        )
        if not already:
            event_hooks.append({"hooks": [{"type": "command", "command": command}]})

    settings_path.write_text(json.dumps(settings, indent=2) + "\n")   # always writes
```

When all three GoC hooks are already registered — the common case on a
repeat `goc install` or every `goc upgrade --keep-local-skills` — the
function still re-serialises the user-owned file through
`json.dumps(..., indent=2)`. That reflows the user's chosen indentation
(e.g. 4-space → 2-space) and re-orders top-level keys, producing a
spurious diff in a file checked into the consumer's source tree.

This is inconsistent with the sibling `_strip_goc_settings_entries`
(same module, lines 656–770), which threads a `changed` flag and guards
its write:

```python
    if changed:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
```

`_merge_claude_settings` already captures `original` at line 574 but
never uses it to suppress a no-op write.

## Empirical evidence

`uv run python .game-of-cards/deck/merge-claude-settings-rewrites-settings-json-on-idempotent-merge/reproduce.py`:

```
semantically equal (no hook needed adding): True
file rewritten (bytes differ):              True

Expected on a no-op merge: file rewritten = False
Actual:                    file rewritten = True

DEFECT CONFIRMED: idempotent merge churned a user-owned file.
```

## Why it matters

`.claude/settings.json` is a **user-owned** file under version control.
`_sync_agent_harness` calls `_merge_claude_settings` unconditionally on
any Claude install/upgrade in vendored/local-skills mode
(`goc install --local-skills` re-run; every `goc upgrade
--keep-local-skills`). The reachability path is plain: a settings file
that already carries the GoC hooks triggers the spurious rewrite with no
special input. Users who hand-format their settings see GoC churn their
indentation and key order on every idempotent upgrade — noisy in code
review and surprising for a tool whose docstring promises to add hooks
"without removing unrelated keys."

## Fix

Mirror `_strip_goc_settings_entries`: thread a `changed` flag through
`_merge_claude_settings`, set it True at each genuine mutation site (the
non-dict/non-list backup-and-reset branches, and the `not already`
append), and guard the final write with `if changed:`. No behavior
change when a hook genuinely needs adding; a no-op merge leaves the
user's bytes untouched. No design decision — the intended behavior is
already demonstrated by the sibling function in the same module.

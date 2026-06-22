---
title: sync-claude-import-overwrites-user-authored-import-line-with-goc-target
summary: "`_sync_claude_import` (`goc/install.py:229-267`) identifies the GoC import line to update by matching against ALL importable targets (`@AGENTS.md`, `@CLAUDE.local.md`), not just the one GoC manages. So a user's hand-authored `@CLAUDE.local.md` import is rewritten to `@AGENTS.md` when GoC's briefing target is the default, destroying the user's import. Sibling of `strip-claude-import-removes-user-authored-import-lines-from-claude-md`; both functions need the same ownership rule for bare import lines."
status: open
stage: null
contribution: medium
created: "2026-06-21T12:03:28Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: ownership rule for bare import lines decided and recorded (see "## Decision required"); coordinate with the sibling card [strip-claude-import-removes-user-authored-import-lines-from-claude-md](../strip-claude-import-removes-user-authored-import-lines-from-claude-md/) so both functions adopt the same rule.
  - [ ] TDD: reproduce.py exits zero after the fix — a user-authored `@CLAUDE.local.md` import (sole line, and amid other content) survives `goc install --agents claude --briefing-target AGENTS.md`.
  - [ ] TDD: regression test — a GoC-owned CLAUDE.md (sole bare import line for the *current* briefing target, or a marker-bounded import block) is still updated to the new briefing target per the chosen rule.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` green; `uv run goc validate` clean.
---

# `_sync_claude_import` overwrites a user-authored import line with GoC's briefing target

## Location

- `goc/install.py:229-267` — `_sync_claude_import`
- `goc/install.py:247-250` — the sole-line early return
- `goc/install.py:257-265` — the bare-line replacement loop
- `goc/install.py:40` — `CLAUDE_IMPORTABLE_TARGETS = ("AGENTS.md", "CLAUDE.local.md")`
- Caller: `_sync_methodology_blocks` (`install.py`, when `briefing_target != "CLAUDE.md"`)

## What's broken

`_sync_claude_import` is meant to maintain *GoC's own* `@<briefing>`
import in a user's `CLAUDE.md`. But it identifies "the GoC import line
to update" by matching against the import lines of **every** importable
target, not just the one GoC manages:

```python
    text, newline = _read_text_keep_newline(claude_md)
    stripped = text.strip()
    import_lines = {f"@{candidate}" for candidate in CLAUDE_IMPORTABLE_TARGETS}
    if not stripped or stripped in import_lines:
        _write_text_keep_newline(claude_md, import_line + "\n", newline)
        return
    ...
    lines = text.splitlines()
    replaced_bare_import = False
    for idx, line in enumerate(lines):
        if line.strip() in import_lines:
            lines[idx] = import_line
            replaced_bare_import = True
    if replaced_bare_import:
        _write_text_keep_newline(claude_md, "\n".join(lines).rstrip() + "\n", newline)
        return
```

with `import_lines = {"@AGENTS.md", "@CLAUDE.local.md"}`.

So when a user has a hand-authored `@CLAUDE.local.md` import (a common
Claude Code pattern for un-checked-in local notes) and GoC's briefing
target is the default `AGENTS.md`, GoC rewrites the user's
`@CLAUDE.local.md` line to `@AGENTS.md` — destroying the user's
local-notes import. The docstring promises "If the user already has
custom CLAUDE.md content, keep it" but the bare-line replacement loop
mutates a line GoC never wrote.

The intended path for non-GoC content is the marker-bounded block at
`install.py:267` (`text.rstrip() + "\n\n" + block`); the bug is that the
union-match short-circuits to overwrite before that path is reached.

## Empirical evidence

`reproduce.py` calls `_sync_claude_import(dir, "AGENTS.md")` against a
`CLAUDE.md` that imports the user's own `@CLAUDE.local.md`:

```
CASE A (sole @CLAUDE.local.md, briefing AGENTS.md):
'@AGENTS.md\n'
  user import preserved? False

CASE B (custom content + @CLAUDE.local.md, briefing AGENTS.md):
'# Project rules\n\nUse tabs.\n\n@AGENTS.md\n'
  user import preserved? False
```

Expected: the user's `@CLAUDE.local.md` survives and GoC adds its own
marker-bounded `@AGENTS.md` import block (case B) or writes its own
import without clobbering an unrelated one (case A).

## Why it matters

This is the maintain-import counterpart of the already-filed
[strip-claude-import-removes-user-authored-import-lines-from-claude-md](../strip-claude-import-removes-user-authored-import-lines-from-claude-md/),
which is in `_strip_claude_import` (the *removal* path, used only when
`--briefing-target CLAUDE.md`). That sibling card explicitly notes
`_sync_claude_import` "shows why ownership of bare lines is ambiguous"
but is scoped to the removal function and leaves this rewrite path
unaddressed.

Both share one root-cause shape: **treating the union of all
`CLAUDE_IMPORTABLE_TARGETS` import lines as GoC-owned, when only the
import for the current briefing target is GoC's to manage.** Two
instances of the same shape; if a third appears, fold them into an
architectural meta-fix (a single "which bare import lines does GoC
own?" helper) rather than patching each site.

Reachability: this fires on the **default** install flag combination
(`--agents claude` with the default `--briefing-target AGENTS.md`) on
any repo whose pre-existing `CLAUDE.md` imports `@CLAUDE.local.md` —
a documented Claude Code convention. It silently mutates authored
content, violating GoC's "never destroy authored content" guarantee.

## Decision required

What counts as a GoC-owned bare import line that `_sync_claude_import`
may rewrite? Candidate rules:

1. **Only the current briefing target.** Match only `@{briefing_target}`,
   never the union. A user's `@CLAUDE.local.md` is left intact and GoC's
   import is added via the marker-bounded block. Simplest; risk: if GoC
   previously managed a *different* briefing target as a bare line, the
   old bare import is orphaned (not cleaned up) when the target changes.
2. **Marker-bounded only.** Treat *no* bare line as GoC-owned; GoC only
   ever manages its import inside `<!-- BEGIN GOC IMPORT -->` markers.
   Fully unambiguous, but a fresh GoC-owned sole-line CLAUDE.md (written
   by line 242) is then no longer recognized as GoC's on a later
   briefing-target change.
3. **Sole-line heuristic.** A bare import is GoC-owned only when it is
   the *entire* file (sole line); any bare import amid other content is
   user-authored and gets the marker block. Matches the line-242 fresh
   write, but a user whose whole CLAUDE.md is just `@CLAUDE.local.md`
   (case A above) is still clobbered.

This is the same ownership question the sibling card is parked on, so
the chosen rule should be applied to **both** `_sync_claude_import` and
`_strip_claude_import` in one coordinated fix.

## Fix

Do NOT apply until the ownership rule is decided. Once decided, replace
the `import_lines` union match at `install.py:247-265` with the chosen
predicate (most likely option 1: match only `@{briefing_target}`,
routing any other bare import through the marker-bounded block path at
line 267), and mirror the same predicate into `_strip_claude_import`.

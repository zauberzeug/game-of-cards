---
title: strip-claude-import-removes-user-authored-import-lines-from-claude-md
summary: "`_strip_claude_import` (run by `goc install`/`goc upgrade` with `--briefing-target CLAUDE.md`) deletes EVERY bare `@AGENTS.md` / `@CLAUDE.local.md` line from CLAUDE.md, not just the import GoC wrote — so a user whose pre-GoC CLAUDE.md imports their own AGENTS.md silently loses that import and Claude stops loading their guidance. Unverified: confirmed by code reading; no end-to-end reproduce.py yet."
status: open
stage: null
contribution: low
created: "2026-06-12T05:19:44Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] PROCESS: ownership rule for bare import lines decided and recorded (see Decision required).
  - [ ] TDD: reproduce.py lands and exits zero after the fix (user-authored bare `@AGENTS.md` amid other CLAUDE.md content survives `goc install --briefing-target CLAUDE.md`); drop the `unverified` tag when it lands.
  - [ ] TDD: regression test — a GoC-owned CLAUDE.md (sole bare import line, or marker-bounded import block) is still cleaned up per the chosen rule.
---

# strip-claude-import-removes-user-authored-import-lines-from-claude-md

## Location

- `goc/install.py:209-226` — `_strip_claude_import`
- `goc/install.py:1266` — sole caller, inside `_sync_methodology_blocks` when `briefing_target == "CLAUDE.md"`
- `goc/install.py:229-268` — `_sync_claude_import`, which shows why ownership of bare lines is ambiguous

## Hypothesis (unverified — code-reading evidence only)

`_strip_claude_import`'s docstring promises "Remove GoC's Claude
import pointer from CLAUDE.md, **preserving user text**", but after
removing the marker-bounded block it also filters *every* bare import
line:

```python
    lines = [
        line
        for line in text.splitlines()
        if line.strip() not in {f"@{target}" for target in CLAUDE_IMPORTABLE_TARGETS}
    ]
```

with `CLAUDE_IMPORTABLE_TARGETS = ("AGENTS.md", "CLAUDE.local.md")`.
A CLAUDE.md that predates GoC and contains the user's own
`@AGENTS.md` import (the exact pattern this repo's CLAUDE.md uses,
and which Claude Code documents) loses that line whenever
`goc install` / `goc upgrade` runs with `--briefing-target CLAUDE.md`
— Claude silently stops loading the user's non-GoC AGENTS.md
guidance.

The ambiguity is real, not an oversight: `_sync_claude_import`
sometimes writes GoC's import as a bare line (fresh file, or file
whose entire content was an import line) and even edits bare lines
amid user content in place (`replaced_bare_import` path,
install.py:257-264). So at strip time GoC genuinely cannot tell
"line I wrote" from "line the user wrote" — the bug is that it
resolves the ambiguity by deleting user content.

## Why it matters

Reachability: any consumer repo that adopted the Claude-standard
`CLAUDE.md → @AGENTS.md` import *before* installing GoC, then runs
`goc install --briefing-target CLAUDE.md` (or later switches the
briefing target to CLAUDE.md and upgrades). The failure is silent —
no file disappears; an import line vanishes and Claude's behavior
degrades without any error.

## Why deferred this round

Surfaced by the audit hunter alongside two higher-contribution
findings that consumed the round's `reproduce.py` budget
([sync-plugin-assets-deletes-user-authored-skills-and-hooks-from-dogfood-dirs](../sync-plugin-assets-deletes-user-authored-skills-and-hooks-from-dogfood-dirs/),
[repair-edges-apply-writes-superseded-by-onto-non-superseded-cards](../repair-edges-apply-writes-superseded-by-onto-non-superseded-cards/)).
The hunter reproduced this one at the function boundary only; the
end-to-end install path is unexercised.

## Falsification recipe

In a temp git repo: write `CLAUDE.md` =
`# Notes\n\nMy own project notes that predate GoC.\n\n@AGENTS.md\n`
plus a user `AGENTS.md` with no GoC markers. Run
`goc install --briefing-target CLAUDE.md --agents claude`. If the
resulting CLAUDE.md still contains the `@AGENTS.md` line, the
hypothesis is falsified (check whether `_sync_methodology_blocks`
gates the strip on something the function-level call missed).
If the line is gone, promote: drop `unverified`, land the recipe as
`reproduce.py`.

## Decision required

How should GoC decide which import lines it owns at strip time?

1. **Marker-block-only strip.** Only remove the marker-bounded import
   block; stop filtering bare lines. GoC-written bare-line files are
   already handled by the "file becomes empty → delete" path, since a
   GoC-owned bare-line CLAUDE.md contains nothing else. Bare lines
   amid user content are then always preserved. Requires
   `_sync_claude_import` to stop *writing/editing* bare lines amid
   user content (always use the marker block there) so ownership
   stays decidable going forward.
2. **Strip only when the file is nothing but import lines.** Keeps
   today's cleanup for GoC-owned files without touching mixed-content
   files; leaves `_sync_claude_import`'s in-place bare-line edit
   path as an acknowledged ownership leak.
3. **Status quo + docs.** Document that `--briefing-target CLAUDE.md`
   removes all top-level import lines. Cheapest, but the silent
   user-content deletion remains.

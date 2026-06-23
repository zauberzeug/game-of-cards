---
title: upgrade-briefing-target-picker-accepts-zero-and-negative-selections
summary: "`goc upgrade`'s multi-block legacy-install picker converts a 1-based selection to a 0-based index with `found[int(raw) - 1]`. Python negative indexing means `0` resolves to `found[-1]` (the last candidate) and any negative number wraps around, so out-of-range input silently selects the WRONG briefing file and strips the block from the others instead of hitting the existing abort branch."
status: done
stage: null
contribution: medium
created: "2026-06-23T01:28:33Z"
closed_at: "2026-06-23T01:32:52Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (picker aborts with SystemExit(2) on `0` and `-1` instead of selecting a file)
  - [x] TDD: a regression test feeds `0\n` and `-1\n` to `_resolve_upgrade_briefing_target` via non-TTY stdin and asserts `SystemExit` with code 2
  - [x] TDD: the same test asserts a valid in-range selection (`2\n`) still resolves to the second candidate (no regression)
  - [x] MECHANICAL: the fix bounds-checks `1 <= idx <= len(found)` before indexing, routing out-of-range numbers into the existing `invalid selection` abort branch
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# `goc upgrade` briefing-target picker accepts `0` and negative selections via Python negative indexing

## Location

`goc/install.py:1557-1564`, inside `_resolve_upgrade_briefing_target` (the
multi-block legacy-install picker).

## What's broken

When a legacy repo has GoC marker blocks in more than one file, `goc upgrade`
prompts the user to pick which file should keep the briefing and strips the
block from the others. The prompt (line 1551) advertises a **1-based** index:

```python
        raw = input(f"Pick [1-{len(found)}, default 1]: ").strip()
```

The selection is then converted to a 0-based list index:

```python
    if not raw:
        choice = found[0]
    else:
        try:
            choice = found[int(raw) - 1]
        except (ValueError, IndexError):
            print(f"goc: error: invalid selection {raw!r}; aborting upgrade.", file=sys.stderr)
            sys.exit(2)
```

The `except (ValueError, IndexError)` branch is meant to reject invalid input,
but it never fires for `0` or negative numbers: Python's list indexing accepts
negative subscripts. `int("0") - 1 == -1` returns `found[-1]` (the **last**
candidate), and any `-k` wraps around from the end instead of raising
`IndexError`. Only an out-of-range *positive* index (e.g. `99`) raises and
aborts. So the one input most likely to mean "none of these / let me out"
(`0`) silently selects the last file and strips the briefing block from the
real briefing home.

## Empirical evidence

```
raw='0'   -> selected 'CLAUDE.local.md'   (EXPECTED: abort)
raw='-1'  -> selected 'CLAUDE.md'         (EXPECTED: abort)
raw='-2'  -> selected 'AGENTS.md'         (EXPECTED: abort)
raw='2'   -> selected 'CLAUDE.md'         (correct in-range selection)
```

(from `reproduce.py`, with `found = ['AGENTS.md', 'CLAUDE.md', 'CLAUDE.local.md']`)

## Why it matters

This is reachable through the real `upgrade` flow without a human in the loop.
When stdin is not a TTY the picker reads `sys.stdin.readline()` (line 1554), so
a scripted / piped `0\n` (or a stray negative value) routes straight into the
buggy index. The consequence is not a crash but a *silent wrong choice*: the
briefing block is preserved in the wrong file and stripped from the others —
the opposite of the documented "abort on invalid input" contract the code
already tries to enforce one line below. There is exactly one site with this
index pattern (`grep 'int(raw)' goc/*.py` → one hit), so this is a single
isolated defect, not a family.

## Fix

Bounds-check before indexing so out-of-range numbers reach the existing abort
branch:

```python
    if not raw:
        choice = found[0]
    else:
        try:
            idx = int(raw)
            if not 1 <= idx <= len(found):
                raise IndexError
            choice = found[idx - 1]
        except (ValueError, IndexError):
            print(f"goc: error: invalid selection {raw!r}; aborting upgrade.", file=sys.stderr)
            sys.exit(2)
```

The abort branch and its `sys.exit(2)` are already correct; they simply were
not being reached for `0`/negatives. One function, one guard — no shared
helper, so the plugin mirrors and sync/port scripts are unaffected.

---
title: closed-since-huge-window-crashes-with-overflowerror-traceback
summary: "`goc --closed-since <huge-window>` (e.g. `99999999999w`) crashes with an uncaught `OverflowError` traceback. `parse_closed_since` rejects non-positive N cleanly (exit 2) but applies no upper bound before `timedelta(hours=...)`, so a syntactically valid but oversized window overflows. Fix: bound-check or wrap the timedelta and emit the same `goc: error: --closed-since: ...` / exit 2 as the other invalid-input branches."
status: open
stage: null
contribution: low
created: "2026-06-23T19:43:04Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (`parse_closed_since("99999999999w")` raises `SystemExit(2)`, not `OverflowError`)
  - [ ] TDD: a regression test asserts an oversized window exits 2 with a `goc: error: --closed-since:` message; valid windows (`24h`, `7d`, `2w`) and absolute dates still parse
  - [ ] MECHANICAL: the fix lives in `parse_closed_since` (`goc/engine.py`) and reuses the existing exit-2 error style
  - [ ] PROCESS: plugin mirrors re-synced; `uv run goc validate` passes and the full `unittest` suite stays green
---

# `goc --closed-since <huge-window>` crashes with an OverflowError traceback

## Location

`goc/engine.py` — `parse_closed_since` (lines 2516-2538), specifically the
`timedelta` construction at line 2538.

## What's broken

`--closed-since` accepts a relative window `<N>[h|d|w]`. The function
validates the *syntax* (regex) and rejects non-positive `N` with a clean
error, but applies **no upper bound** before passing to `timedelta`:

```python
        if n <= 0:
            print(
                "goc: error: --closed-since: window must be a positive integer "
                "(e.g. 24h, 7d, 2w)",
                file=sys.stderr,
            )
            sys.exit(2)
        hours = {"h": n, "d": n * 24, "w": n * 24 * 7}[unit]
        return base - timedelta(hours=hours)
```

A syntactically valid but very large window (e.g. `99999999999w`) produces
an `hours` value beyond `timedelta`'s C-int range, so
`timedelta(hours=hours)` raises `OverflowError`. The exception is uncaught
— the CLI dies with a full Python traceback and a non-clean exit instead
of the orderly `goc: error: --closed-since: ...` / `sys.exit(2)` that
every other invalid input on this flag produces (`0h` →
"must be a positive integer"; `abc` → "expected <N>[h|d|w] or
YYYY-MM-DD").

## Empirical evidence

`uv run python .game-of-cards/deck/closed-since-huge-window-crashes-with-overflowerror-traceback/reproduce.py`:

```
DEFECT CONFIRMED: OverflowError instead of clean exit 2 -> Python int too large to convert to C int
```

Equivalently, `uv run goc --closed-since 99999999999w` prints a
`Traceback (most recent call last): ... OverflowError: Python int too
large to convert to C int`.

## Why it matters

`--closed-since` is user-facing CLI input (the `--done` / closed-card
queries). A degenerate-but-valid argument should produce a tidy
diagnostic, not a stack trace — the same UX contract the function already
honors for `0h` and `abc`. Reachability: the argparse layer hands the raw
string straight to `parse_closed_since`; any oversized integer window
reaches the unbounded `timedelta`.

## Fix

After computing `hours`, either bound-check it or wrap the `timedelta`
call in `try/except OverflowError`, emitting the same
`goc: error: --closed-since: ...` / `sys.exit(2)` as the sibling
invalid-input branches:

```python
        try:
            return base - timedelta(hours=hours)
        except OverflowError:
            print(
                "goc: error: --closed-since: window too large",
                file=sys.stderr,
            )
            sys.exit(2)
```

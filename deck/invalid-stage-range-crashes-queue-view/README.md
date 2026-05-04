---
title: invalid-stage-range-crashes-queue-view
summary: "Passing an invalid stage range such as `--stage foo-bar` crashes the queue view with a Python traceback instead of returning a normal CLI validation error."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] reproduce.py exits zero (invalid stage ranges no longer traceback)
  - [x] `goc --stage foo-bar` exits non-zero with a concise Click error
  - [x] valid stage filters and ranges still work
  - [x] `goc validate` passes after the CLI validation fix
---

# invalid-stage-range-crashes-queue-view

## Location

`goc/engine.py:866` parses `--stage` after Click has accepted the raw string.

## What's broken

The queue command accepts arbitrary `--stage` strings. Single invalid values
just produce an empty queue, but invalid ranges crash inside list lookup:

```text
ValueError: 'foo' is not in list
```

The crashing code is:

```python
if "-" in stage_flag:
    order = ["null", "alpha", "beta", "stable"]
    a, b = stage_flag.split("-", 1)
    ai, bi = order.index(a), order.index(b)
```

## Empirical evidence

Before the fix, `uv run goc --stage foo-bar` exits 1 and prints a traceback
ending in `ValueError: 'foo' is not in list`.

## Why it matters

`--stage` is a public queue filter. Bad user input should be rejected as a
normal CLI usage error, not as an internal traceback that looks like an engine
crash.

## Fix

Validate stage atoms against `null`, `alpha`, `beta`, and `stable` before
building the range. Invalid values should raise a Click parameter error with
a concise message. Keep valid single-stage filters and valid reverse ranges
such as `stable-alpha` working.

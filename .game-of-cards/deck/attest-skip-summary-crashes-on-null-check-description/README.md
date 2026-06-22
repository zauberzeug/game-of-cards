---
title: attest-skip-summary-crashes-on-null-check-description
status: done
stage: null
contribution: medium
created: "2026-06-22T02:23:37Z"
closed_at: "2026-06-22T02:30:01Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a regression test builds the skipped-check result dict (or runs `_cmd_attest`) with a check whose `description` is `None` and asserts no `TypeError` and a `SKIPPED (...)` summary
  - [x] TDD: the same path with an absent `description` key and a non-empty `description` string still produce the previously-correct summaries (no regression)
  - [x] MECHANICAL: line 4495 uses null-coalescing `(check.get('description') or '')[:60]`
  - [x] reproduce.py exits zero (the crash no longer fires) on a clean checkout
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `goc attest` crashes on a skipped check whose `description` is null

## Summary

`goc attest` raises an uncaught `TypeError` when a *skipped* closure
check's config entry carries an explicit `description: null`. The skip
branch slices `check.get('description', '')[:60]`, whose `''` default
only guards an *absent* key — a present-but-`None` value slips through
and `None[:60]` blows up.

## Location

`goc/engine.py:4495`, in `_cmd_attest`'s skip branch:

```python
if name in skips_set:
    results.append(
        {
            "layer": layer_num,
            "name": name,
            "passed": True,
            "skipped": True,
            "summary": f"SKIPPED ({check.get('description', '')[:60]})",  # line 4495
        }
    )
    print(f"  [~] {name} — SKIPPED")
    continue
```

## What's broken

`dict.get(key, default)` returns `default` only when `key` is *absent*.
When the config check is written as `description: null` (a valid YAML
value), the key is present with value `None`, so `.get('description', '')`
returns `None`, and `None[:60]` raises:

```
TypeError: 'NoneType' object is not subscriptable
```

The `''` default was clearly intended to mean "no description → render
an empty parenthetical." An explicitly-null description means exactly
the same thing to a reader, yet it crashes the whole `attest` run with a
full traceback and exit 1.

Note the all-skipped guard at `engine.py:4471` returns early (exit 2)
only when *every* configured check is skipped, so the crash requires at
least one non-skipped sibling check to reach the loop body at 4486.

## Empirical evidence

`reproduce.py` drives the real `goc` CLI end-to-end in a throwaway repo
(install → config with a null-description skipped check + a running
sibling → `goc attest --skip`).

Before the fix the attest run crashes at line 4495:

```
goc attest returncode: 1
Layer-3 (GoC) checks:
  [x] dod-100-percent — 1/1 ticked
...
  File ".../goc/engine.py", line 4495, in _cmd_attest
    "summary": f"SKIPPED ({check.get('description', '')[:60]})",
TypeError: 'NoneType' object is not subscriptable
FAIL: attest crashed with TypeError on a null check description
```

After the fix it renders the skipped line and completes:

```
Layer-3 (GoC) checks:
  [x] dod-100-percent — 1/1 ticked
  [~] log-md-closure-entry — SKIPPED
Attestation OK.
PASS: null check description rendered as SKIPPED, no crash
```

## Why it matters

The config loader does not strip null-valued keys, so a check authored
as `description: null` (or `description:` with no value, which YAML
parses to `None`) flows verbatim into the per-check dict that
`_cmd_attest` iterates. A consumer editing `.game-of-cards/config.yaml`
who blanks out a description while leaving the key in place, then runs
`goc attest <card> --skip <that-check>`, gets an opaque Python traceback
instead of the intended `[~] <name> — SKIPPED` line. This is the
documented closure-attestation path (`goc attest`, `bundled-closure`),
so the crash is reachable from a routine config edit, not a synthetic
input.

## Fix

Use the standard null-coalescing form so a present-but-null description
renders identically to an absent one:

```python
"summary": f"SKIPPED ({(check.get('description') or '')[:60]})",
```

Single-site: line 4495 is the only place a check's `description` is
sliced (the sibling `prompt` / `rationale_prompt` lookups feed f-strings
and `input()`, which stringify `None` harmlessly), so this is not a
meta-fix family.

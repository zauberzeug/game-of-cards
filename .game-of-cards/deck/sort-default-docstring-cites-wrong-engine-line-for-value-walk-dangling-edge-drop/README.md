---
title: sort-default-docstring-cites-wrong-engine-line-for-value-walk-dangling-edge-drop
status: done
stage: null
contribution: low
created: "2026-06-24T13:57:19Z"
closed_at: "2026-06-24T14:01:40Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, meta-fix, bug]
definition_of_done: |
  - [x] `sort_default`'s docstring no longer cites a hardcoded `engine.py:NNNN`
        line for the value walk's dangling-edge drop.
  - [x] The cross-reference instead names the symbol it points at
        (`compute_values`'s `value_for`), so it cannot rot when line numbers shift.
  - [x] `reproduce.py` asserts no `engine.py:NNNN` hardcoded line citation
        remains in `sort_default.__doc__` and that it names `value_for`.
        (Durably guarded by `tests/test_guidance_accuracy.py::DocstringCitationAccuracyTest`.)
  - [x] `uv run python -m unittest discover -s tests` passes.
  - [x] `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# `sort_default` docstring cites the wrong `engine.py` line for the value walk's dangling-edge drop

## Problem

`sort_default` (`goc/engine.py:2599`) is the central ordering function behind
every queue, board, and `next-card`/`pull-card` decision. Its docstring
explains why a *genuinely dangling* `advances` edge (target absent from the
whole deck) contributes 0 to the near-term-flow tiebreak, and cross-references
the analogous prune in the value walk:

```
goc/engine.py:2625-2627
    deck — counts 0, because `card_is_workable_for_scheduler` never sees it,
    matching the value walk's dangling-edge drop at engine.py:1739. When
```

The cited line `engine.py:1739` is **wrong**. Line 1739 is inside
`_would_create_advance_cycle` — an unrelated cycle-detection helper:

```
goc/engine.py:1739
        if card is None:
            continue
```

The value walk's actual dangling-edge drop is in `compute_values`'s nested
`value_for`, at `engine.py:2382`:

```
goc/engine.py:2382-2391
        for dest in advances:
            if dest not in by_title:
                key = (title, dest)
                if key not in _DANGLING_ADVANCES_WARNED:
                    _DANGLING_ADVANCES_WARNED.add(key)
                    print(
                        f"WARN dangling advances edge: {title} → {dest!r} "
                        ...
                continue
```

This is the only hardcoded `engine.py:NNNN` self-citation in the file
(`grep -n 'engine\.py:[0-9]' goc/engine.py` returns exactly this one line).

## Why it matters

A maintainer reading `sort_default`'s rationale — to verify the "dangling edges
count 0" invariant the tiebreak depends on — follows the cross-reference to
`engine.py:1739` and lands in `_would_create_advance_cycle`, code that has
nothing to do with the value/tiebreak walk. The citation actively misleads
verification of a non-obvious scheduling invariant.

It is also a textbook instance of the "defunct file:line reference" class that
`refine-deck` is meant to catch: a hardcoded line number drifted out of sync as
surrounding code shifted. The drift-proof fix is to cite the *symbol*
(`compute_values`'s `value_for`) rather than re-pin a line number that will rot
again.

## Reachability

`grep -n 'engine\.py:[0-9]'` over `goc/engine.py` deterministically surfaces the
stale citation; the surrounding line text confirms `1739` resolves to
`_would_create_advance_cycle`, not the value walk. No card authoring or runtime
input is needed — the defect lives in shipping source and is reproduced by
inspecting the source itself.

## Fix

Replace the line-number citation in `sort_default.__doc__` with a symbol
reference:

> matching the value walk's dangling-edge drop in `compute_values`'s `value_for`.

This documents the same invariant, points at the correct code, and does not rot
when line numbers shift.

## Verification

`reproduce.py` reads `sort_default.__doc__`, asserts no `engine.py:NNNN`
hardcoded line citation survives, and asserts the docstring names `value_for`.
Before the fix it prints `FAIL`; after, `OK`.

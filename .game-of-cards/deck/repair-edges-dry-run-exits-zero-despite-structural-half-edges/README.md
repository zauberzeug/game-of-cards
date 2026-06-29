---
title: repair-edges-dry-run-exits-zero-despite-structural-half-edges
summary: "`goc repair-edges` dry-run prints structural half-edge problems then exits 0, while `--apply` exits 1 on the same input. A CI gate or &&-chained script using the safe read-only preview silently passes a deck carrying half-edges no verb can auto-fix. The two modes must agree on the success contract."
status: done
stage: null
contribution: medium
created: "2026-06-29T01:34:22Z"
closed_at: "2026-06-29T01:40:18Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (asserts dry-run returns 1 when the deck has a structural half-edge, matching `--apply`)
  - [x] TDD: a regression test in tests/ covers the dry-run exit-code parity with `--apply`
  - [x] MECHANICAL: the dry-run branch in `_cmd_repair_edges` exits non-zero when `structural` is non-empty, mirroring the apply branch
  - [x] PROCESS: `uv run python -m unittest discover -s tests` passes
  - [x] PROCESS: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `goc repair-edges` dry-run exits 0 even when unfixable structural half-edges remain

## Location

`goc/engine.py:5335-5347` — the `if not args.apply:` dry-run branch of
`_cmd_repair_edges`, asymmetric with the `--apply` branch at
`goc/engine.py:5364-5366`.

## What's broken

`_classify_half_edges` splits half-edges into `fixable` (a missing reverse
half a verb can write) and `structural` (a half-edge whose repair would
create a cycle — no verb can auto-fix it; it needs human review). Both the
dry-run preview and `--apply` share that classification.

The apply branch ends with a hard-failure guard:

```python
    _print_structural_edge_problems(structural)
    if structural:
        sys.exit(1)
```

The dry-run branch prints the same structural problems, then returns with
exit 0 regardless:

```python
    if not args.apply:
        if fixable:
            print(f"Half-edges that would be repaired ({len(fixable)}):")
            ...
        _print_structural_edge_problems(structural)
        print("\nDry run — no changes made. Run 'goc repair-edges --apply' to write fixes.")
        return        # <-- always exit 0, even when `structural` is non-empty
```

So for byte-identical decks, the read-only preview and the executor
disagree on the success contract: `--apply` signals failure (exit 1) on an
unfixable structural half-edge, while the bare `goc repair-edges` preview
that just printed `Structural problems requiring human review:` exits 0.

## Empirical evidence

Before the fix the read-only preview reported clean (exit 0) on a deck the
executor rejected (exit 1):

```
dry-run exit code: 0
--apply  exit code: 1
```

After the fix, `reproduce.py` confirms both modes agree:

```
dry-run exit code: 1
--apply  exit code: 1

PASS: both modes agree (exit 1) on structural half-edges
```

(See `reproduce.py` for the generator.)

## Why it matters

The read-only dry-run is exactly what a CI gate or an `&&`-chained shell
script reaches for to detect un-repairable edge problems *without*
mutating the deck. Because it exits 0 even after printing "Structural
problems requiring human review," such a gate silently passes a deck that
carries half-edges no verb can fix — the same class of problem `--apply`
treats as a hard failure.

Reachability: a structural half-edge arises whenever a card hand-edit (or
a partial mutation) leaves one side of an `advances`/`advanced_by` pair
written such that completing the reverse half would close a cycle. The
closed sibling
[repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses](../repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses/)
already established that dry-run and apply must agree on the *fixable set*;
this card extends the same parity principle to the *exit code*.

## Fix

In the dry-run branch of `_cmd_repair_edges`, mirror the apply branch's
terminal guard — replace the bare `return` with an exit guard:

```python
        print("\nDry run — no changes made. Run 'goc repair-edges --apply' to write fixes.")
        if structural:
            sys.exit(1)
        return
```

so the read-only preview signals the same non-zero exit on unfixable
structural half-edges that `--apply` does.

---
title: repair-edges-dry-run-exits-zero-despite-structural-half-edges
summary: "`goc repair-edges` dry-run prints structural half-edge problems then exits 0, while `--apply` exits 1 on the same input. A CI gate or &&-chained script using the safe read-only preview silently passes a deck carrying half-edges no verb can auto-fix. The two modes must agree on the success contract."
status: active
stage: null
contribution: medium
created: "2026-06-29T01:34:22Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (asserts dry-run returns 1 when the deck has a structural half-edge, matching `--apply`)
  - [ ] TDD: a regression test in tests/ covers the dry-run exit-code parity with `--apply`
  - [ ] MECHANICAL: the dry-run branch in `_cmd_repair_edges` exits non-zero when `structural` is non-empty, mirroring the apply branch
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` passes
  - [ ] PROCESS: `uv run goc validate` passes
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

```
=== Dry-run with ONLY structural problems ===
Structural problems requiring human review:
  cyc-a: advances contains 'cyc-b' but cyc-b.advanced_by is missing 'cyc-a' (half-edge): cyc-a -> cyc-b would create a cycle in the advances graph
  cyc-b: advances contains 'cyc-a' but cyc-a.advanced_by is missing 'cyc-b' (half-edge): cyc-b -> cyc-a would create a cycle in the advances graph
Dry run -- no changes made. Run 'goc repair-edges --apply' to write fixes.
DRY-RUN exit=0          <-- reports clean

=== --apply on the SAME deck ===
APPLY exit=1            <-- reports failure
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

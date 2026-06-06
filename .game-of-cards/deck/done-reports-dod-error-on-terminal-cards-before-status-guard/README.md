---
title: done-reports-dod-error-on-terminal-cards-before-status-guard
summary: "`goc done` checks DoD completeness before the terminal-status guard, so a `disproved`/`superseded` card with unchecked DoD boxes is refused with the misleading 'N unchecked DoD boxes' message instead of the authoritative 'status is terminal' diagnostic the code already intends to emit. `_cmd_done_bundle` has the identical inversion."
status: done
stage: null
contribution: medium
created: "2026-06-06T05:26:35Z"
closed_at: "2026-06-06T05:30:20Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (a disproved card with an unchecked DoD box, passed to `goc done`, now refuses with the terminal-status message, not the DoD message)
  - [x] TDD: regression test asserts `goc done` on a terminal card with `dod_open > 0` emits "status is 'disproved' (terminal)" and not "unchecked DoD boxes"
  - [x] MECHANICAL: the status guards (already-done, terminal) run before the DoD checks in both `_cmd_done` and `_cmd_done_bundle`
worker: {who: "claude[bot]", where: main}
---

# done-reports-dod-error-on-terminal-cards-before-status-guard

## Location

- `goc/engine.py:3556-3572` (`_cmd_done`, single-card path)
- `goc/engine.py:3629-3653` (`_cmd_done_bundle`)

## What's broken

`_cmd_done` runs the DoD-completeness gate *before* the status guards:

```python
if t.dod_freeform and not force:
    print(f"ERROR: {title}: free-form DoD; use --force to bypass enforcement", file=sys.stderr)
    sys.exit(2)
if t.dod_open > 0:
    print(f"ERROR: {title}: {t.dod_open} unchecked DoD boxes; will not mark done", file=sys.stderr)
    sys.exit(2)
prior = t.status
if prior == "done":
    print(f"{title}: already done; closed_at unchanged")
    return
if prior in TERMINAL_STATUSES:
    print(
        f"ERROR: {title}: status is {prior!r} (terminal); "
        f"use the supersede/disprove workflow — 'done' cannot overwrite terminal states",
        file=sys.stderr,
    )
    sys.exit(2)
```

A `disproved` or `superseded` card legitimately carries unchecked DoD
boxes — it was closed *without* completing its checklist, which is the
whole point of disproving. When such a terminal card is passed to `goc
done`, control exits on the `dod_open > 0` branch and prints "N
unchecked DoD boxes; will not mark done". The terminal-status guard at
line 3566 — which the code clearly intends as the authoritative refusal
— is shadowed and never reached.

This directly undermines the contract established by the closed card
[done-command-overwrites-terminal-cards](../done-command-overwrites-terminal-cards/),
whose DoD #3 requires that "the refusal message tells the user to use
the appropriate supersede/disprove workflow". That message is exactly
what gets suppressed when the terminal card also has open DoD boxes.

`_cmd_done_bundle` (lines 3629/3635 before 3641/3647) has the identical
ordering inversion.

## Why it matters

The terminal-status check is the semantically authoritative refusal: a
closed card cannot be re-closed regardless of DoD state. Ordering the
DoD check first makes the tool lie about *why* it refused — a user
seeing "unchecked DoD boxes" on a `disproved` card may dutifully check
the boxes and retry, only to then hit the real terminal error, or
conclude the card file is corrupt.

Reachability: the offending input is any card already in a terminal
non-done state with an incomplete checklist. `goc status <t> disproved`
and `goc status <t> superseded` close cards without touching DoD boxes,
so such cards are the normal product of the disprove/supersede
workflow — not a hypothetical shape.

## Fix (applied)

The `prior == "done"` / `prior in TERMINAL_STATUSES` status guards now
run *before* the `dod_freeform` / `dod_open` checks in `_cmd_done`, and
the same reordering was applied to the per-member loop in
`_cmd_done_bundle`. The status of the card is the authoritative gate;
DoD completeness only matters for a card that is actually eligible to
be closed. `reproduce.py` now exits zero (terminal-status message
wins), and two regression tests in
`tests/test_close_terminal_gate_guard.py` pin both the single-card and
bundle paths.

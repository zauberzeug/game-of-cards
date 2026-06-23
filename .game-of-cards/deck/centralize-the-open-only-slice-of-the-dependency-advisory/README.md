---
title: centralize-the-open-only-slice-of-the-dependency-advisory
status: done
stage: null
contribution: medium
created: "2026-06-23T09:01:34Z"
closed_at: "2026-06-23T13:23:52Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix, api-contract]
definition_of_done: |
  - [x] MECHANICAL: the `status == "open"` slice for the dependency advisory is expressed once (a shared helper or a `queue_only`-style parameter on `dependency_advisory`), and both human-facing renderers — `render_table` and `render_board`'s `card_cell` — consume it instead of each inlining `t.status == "open"`.
  - [x] TDD: a unit test pins the helper's contract — open card with an open prereq → advisory shown; active/terminal card with the same prereq → advisory suppressed; and asserts table and board agree for each.
  - [x] TDD: existing regressions still pass — `tests/test_verbose_table_awaiting_liveness.py` (terminal + active cases), `tests/test_board.py`, and the JSON liveness test — with no behavior change to any renderer.
  - [x] MECHANICAL: the JSON renderer is left consuming the terminal-only `dependency_advisory` (machine surface keeps the raw advisory + separate `ready` field) — the consolidation must not silently fold the open-only slice into JSON.
  - [x] `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# Centralize the open-only slice of the dependency advisory

Follow-on to the closed meta-fix
[renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift](../renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift/),
surfaced while fixing
[verbose-table-shows-awaiting-prereq-line-on-active-cards](../verbose-table-shows-awaiting-prereq-line-on-active-cards/).

## The pattern

The dependency advisory ("awaiting: X — you may start") is gated along
**two** independent status dimensions:

1. **Terminal gate** — never show it on `done`/`disproved`/`superseded`.
   The earlier meta-fix centralized this into the `dependency_advisory`
   helper (`goc/engine.py`), and all three renderers (table, board,
   JSON) now consume it.
2. **Open-only slice** — the two *human-facing* renderers additionally
   suppress the advisory on `active` cards: "you may start" is a
   pull-queue hint with no audience once a card is claimed. JSON, a
   machine surface, deliberately does *not* apply this slice (it exposes
   the raw `dependency_awaiting` advisory plus a separate, status-gated
   `ready` field).

The meta-fix centralized dimension (1) but left dimension (2) inlined.
The board carried `t.status == "open"` in its `card_cell` not-ready gate
from the start; the table never had it — which **drifted into a shipping
bug** (`verbose-table-shows-awaiting-prereq-line-on-active-cards`: the
table flagged active cards the board did not). That bug was fixed by
inlining the *same* `t.status == "open"` guard into `render_table`. So
the open-only slice now lives as two independent copies — exactly the
"each renderer re-applies the same guard" shape the meta-fix exists to
eliminate, one dimension deeper.

## Why it matters

Two copies of the open-only guard means the next change to the
slice's semantics (or a fourth renderer / export surface) must edit
both `render_table` and `render_board` in lockstep, or drift again.
The family has already produced one shipping bug per un-centralized
dimension; this is the second dimension and it has already cost one
bug. Centralizing it closes the family.

## Fix

Express the open-only slice once. Candidate shape (matching how the
terminal gate was centralized): give the human-facing renderers a
shared accessor — e.g. `dependency_advisory(card, by_title,
queue_only=True)` that returns `([], False)` unless `card.status ==
"open"`, while the default (`queue_only=False`) keeps the
terminal-only contract JSON relies on. Then:

- `render_table` and `render_board`'s `card_cell` call the
  `queue_only=True` form.
- `render_json` keeps the default terminal-only form.

This is pure consolidation — the shipped behavior after the
`verbose-table-...` fix is already correct; this card removes the
duplicated guard so it cannot drift a third time. No `decision` gate:
the behavior is fully determined (table + board = open-only, JSON =
terminal-only), only the helper's surface shape is at the implementer's
discretion, exactly as the original meta-fix's helper signature was.

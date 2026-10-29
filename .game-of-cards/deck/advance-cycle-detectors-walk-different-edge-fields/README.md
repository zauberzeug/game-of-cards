---
title: advance-cycle-detectors-walk-different-edge-fields
summary: "The goc validate cycle gate `detect_advance_cycles` walked `advanced_by` while the edge-add guard `_would_create_advance_cycle` (consulted by goc advance, goc new and goc repair-edges) walks `advances`, so on a half-edged deck the two reached opposite verdicts about one cycle — reproduce.py confirmed it in both directions. Fixed: the gate walks `advances`, the field the guard and the `compute_values` priority walk read, and its error names that field."
status: done
stage: null
contribution: medium
created: "2026-05-27T14:02:43Z"
closed_at: "2026-10-29T05:09:57Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py builds a deck with cycle `a→b→c→a` written only in `advances` and shows `detect_advance_cycles(cards)` returns `[]` while `_would_create_advance_cycle` reports the cycle — or disproves the divergence. — confirmed against the pre-fix engine (exit 1), plus the mirror case (cycle only in `advanced_by`: the gate reported it, the guard let it through) and two controls; exits 0 after the fix.
  - [x] PROCESS: decide whether the two detectors should walk a single canonical field (and which) or whether `validate_bidirectional_edges` already makes the divergence unreachable on any deck `goc validate` accepts. Record verdict in log.md. — one field, `advances`; the bound only keeps the divergence off decks `goc validate` accepts, while `goc repair-edges` runs the guard on nothing but half-edged decks. Verdict in log.md.
  - [x] MECHANICAL: if a real divergence is confirmed, align both walkers on the same field; drop the `unverified` tag once reproduce.py lands. — `detect_advance_cycles` walks `advances`; `unverified` dropped; regression test `tests/test_advance_cycle_walkers_agree.py`.
worker: {who: "claude[bot]", where: main}
---

# Advance cycle detectors walk different edge fields

## Location

- `detect_advance_cycles` — `goc/engine.py:2298`, the gate `goc validate`
  runs. Walked `advanced_by`; now walks `advances` (`goc/engine.py:2324`).
- `_would_create_advance_cycle` — `goc/engine.py:2334`, the guard
  `goc advance`, `goc new --advanced-by` and `goc repair-edges` consult
  before writing an edge. Walks `advances` (`goc/engine.py:2354`); unchanged.
- `compute_values` — `goc/engine.py:3186`, the priority walk. Reads
  `advances`, and its docstring names the gate as what keeps that input
  acyclic.

## What was broken

The two functions that answer "is there an advance cycle?" read opposite
fields. `advances` and `advanced_by` hold the same edges only on a deck
without half-edges, so where one half of an edge was missing the gate and
the guard disagreed about the same cycle. `reproduce.py` builds three-card
decks whose logical edges a→b→c→a are recorded in one field only:

| Fixture | gate, pre-fix | guard |
|---|---|---|
| cycle only in `advances` (the filed recipe) | no cycle | refuses every edge |
| cycle only in `advanced_by` | reports it | lets every edge through |
| cycle in both fields (control) | reports it | refuses |
| acyclic chain in both fields (control) | nothing | nothing |

The bound the card was filed under — `validate_bidirectional_edges` rejects
every half-edged deck — kept the divergence off decks `goc validate`
*accepts*, not off the decks the walkers run on. `goc validate` runs the gate
on decks that fail it, and `goc repair-edges` runs the guard on nothing but
half-edged decks. The bound protected the exit code, not the verdicts.

## Fix

Both walkers read `advances`. The gate now walks the field the guard already
walked and the `compute_values` walk reads. Its error names the field it
walked, with the arrow in the value-flow direction the guard's own refusal
uses: `a: advances: cycle detected through c → a` (c advances a), where it
read `a: advanced_by: cycle detected through b → a`.

`advances` rather than `advanced_by`, because:

- **No write path moves.** The guard gates three mutation verbs, and its
  `advances` walk is what the `goc repair-edges` regression tests pin.
  Changing the read-only gate changes no write.
- **It is the field a cycle silently corrupts.** A cycle in `advances` makes
  `compute_values` return order-dependent priorities with no error. A cycle
  in `advanced_by` stalls closure loudly: the `advanced-by-closed` check
  names the open prereq.

## Residual, by design

A cycle recorded only in `advanced_by` is now read by neither walker; the
gate used to report it. It stays bounded. Its half-edges fail
`goc validate` on their own, and `goc repair-edges` repairs every edge
except the one that would close the cycle in `advances`, which it reports
as structural (reproduce.py: 2 fixable, 1 structural).

Walking the union of both fields would see every recorded cycle. That is the
edge set `goc repair-edges` already assumes, since it completes a half-edge
rather than dropping it. It was weighed and not taken. It departs from the
decision's single field, and it changes `goc repair-edges`: an
`advanced_by`-recorded cycle would have every edge refused instead of all but
one repaired, which re-pins
`test_repair_edges_dry_run_matches_apply_on_interacting_half_edges` from 1
fixable edge to 0. That is a behavior call for a human, not part of this fix.

## Regression guard

- `tests/test_advance_cycle_walkers_agree.py` — the gate and the guard reach
  one verdict on all four fixtures, and the error names `advances`. Three
  of its five tests fail against the pre-fix engine.
- `tests/test_non_list_advances_guard.py` — the non-list test now feeds the
  gate a bare-string `advances`, the field it reads. It fails if the walker
  drops its `isinstance` guard.

Surfaced by: general-purpose audit hunter (engine seam), 2026-05-27.

## Decision

*Resolved 2026-10-22T05:56:36Z:* Lower the gate: verify the hypothesis with a reproduce.py first, then make both cycle walkers read one edge field

*Reasoning:* Bulk rule approved by the maintainer in a human session on 2026-10-22: a gated card with no written question and a mechanical fix drops to gate none

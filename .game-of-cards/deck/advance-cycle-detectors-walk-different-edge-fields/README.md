---
title: advance-cycle-detectors-walk-different-edge-fields
summary: "UNVERIFIED. The gating validator `detect_advance_cycles` (goc/engine.py:~1323) walks the `advanced_by` field, while the live edge-add guard `_would_create_advance_cycle` (goc/engine.py:1349) walks the `advances` field. On a half-edged deck (only one side populated) the two can return opposite verdicts about the same logical cycle, so `goc validate` may pass a cycle the `goc advance` guard would have refused. Bounded: on a validate-clean (bidirectionally-edged) deck both fields agree."
status: open
stage: null
contribution: medium
created: "2026-05-27T14:02:43Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py builds a deck with cycle `a→b→c→a` written only in `advances` and shows `detect_advance_cycles(cards)` returns `[]` while `_would_create_advance_cycle` reports the cycle — or disproves the divergence.
  - [ ] PROCESS: decide whether the two detectors should walk a single canonical field (and which) or whether `validate_bidirectional_edges` already makes the divergence unreachable on any deck `goc validate` accepts. Record verdict in log.md.
  - [ ] MECHANICAL: if a real divergence is confirmed, align both walkers on the same field; drop the `unverified` tag once reproduce.py lands.
---

# Advance cycle detectors walk different edge fields

> **UNVERIFIED** — surfaced by an audit hunter; citations checked but no
> `reproduce.py` written this round. Falsification recipe below.

## Location

- `detect_advance_cycles` — `goc/engine.py:~1323`: walks `advanced_by`
  (`advanced_by = t.frontmatter.get("advanced_by") or []`).
- `_would_create_advance_cycle` — `goc/engine.py:1349`: walks `advances`
  (`for a in card.frontmatter.get("advances") or []`).

## Hypothesis

The two functions that decide "is there an advance cycle?" read opposite
fields. `detect_advance_cycles` is the gating validator (run by `goc
validate`); `_would_create_advance_cycle` is the live guard that `goc
advance` consults before adding an edge. On a deck where only one side of
the bidirectional edge is populated (a "half-edge"), the two can disagree:
a cycle expressed purely in `advances` is invisible to the `advanced_by`
walker, so `goc validate` reports no cycle while the live guard would have
refused the edge.

## Why it may not matter (the bound)

`validate_bidirectional_edges` flags half-edges as a separate error. On
any deck that passes `goc validate` (both sides populated), the `advances`
and `advanced_by` graphs are mirror images and the two detectors agree.
The divergence is only reachable on a deck that already fails validation
for a different reason — which weakens the practical impact and is why
this is filed `unverified` rather than as a confirmed defect. The decision
gate is: is this a latent correctness asymmetry worth aligning, or
unreachable-by-construction defensive redundancy?

## Falsification recipe

Build three Cards `a`, `b`, `c` with `advances` edges `a→b`, `b→c`, `c→a`
and **empty** `advanced_by` on all three. Assert:

- `engine.detect_advance_cycles(cards) == []`  (walker sees no cycle)
- `engine._would_create_advance_cycle(cards, "a", "c")` is `True`  (guard sees the path)

If both report the cycle, the hypothesis is disproved — flip to `disproved`.

Surfaced by: general-purpose audit hunter (engine seam), 2026-05-27.

---
title: goc-validate-warns-on-stale-blocked-orphan-blocked-and-cascade-roots
summary: |-
  `goc validate` enforces schema and DAG integrity but not state coherence:
  it never flags a `status: blocked` card whose `advanced_by` blockers are
  all closed (stale-blocked), whose `advanced_by` is empty with the real
  blocker named only in the body (orphan-blocked), or whose blocked chain
  terminates at a single human decision gate (cascade-chain root). Add
  three WARN-class checks so graph walkers can see what triage walkers
  already see.
status: done
stage: null
contribution: medium
created: "2026-05-21T08:29:31Z"
closed_at: "2026-05-21T08:36:48Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] `validate_blocker_coherence(cards)` in `goc/engine.py` returns
    structured warnings for STALE_BLOCKED and ORPHAN_BLOCKED cards.
  - [x] CASCADE_CHAIN_ROOT warning fires when ≥3 cards transitively
    `advanced_by`-reach a single `human_gate: decision` card.
  - [x] ORPHAN_BLOCKED is suppressed when `human_gate != none` (Option B
    cluster-park accommodation — a raised gate names the bottleneck,
    whether it's `decision` or `session`).
  - [x] `_cmd_validate` emits warnings as `WARN <CLASS> <card>: <detail>`
    on stderr without contributing to the error-count or exit code.
  - [x] `tests/test_validate_blocker_coherence.py` covers each warning
    class plus the ORPHAN_BLOCKED-suppression edge case.
  - [x] `uv run goc validate` runs clean (or only emits warnings) on this
    repo's own deck.
worker: {who: Rodja Trappe, where: main}
---

# goc-validate-warns-on-stale-blocked-orphan-blocked-and-cascade-roots

## Problem

`goc validate` is well-tuned for **schema** conformance — frontmatter
fields, tag canonicality, `advances ↔ advanced_by` bidirectional graph
integrity, DAG acyclicity. But it does NOT check **state coherence**:
whether a card's `status` is consistent with its blocker graph.

In a real-world deck (external repo, 2026-05-21 scan), 8 of 20
`status: blocked` cards exhibited blocker-graph incoherence:

| Failure mode          | Count | Cause                                                                                          |
| --------------------- | ----- | ---------------------------------------------------------------------------------------------- |
| **Stale-blocked**     | 1     | All `advanced_by` entries are `done` / `superseded` / `disproved`; no active prereq remains    |
| **Orphan-blocked**    | 2     | `advanced_by` is empty; real blocker named in body but invisible to graph walkers              |
| **Partial-blocked**   | 5     | ≥1 inactive blocker mixed with active ones (legitimately blocked, but worth surfacing)         |
| **Mutual-park cycle** | 2     | Body-named blocker would create a cycle if hoisted to `advanced_by` — cluster-park has no edge |

These never trip `goc validate` because the validator walks the graph
for structural integrity, not for `status`-vs-graph coherence.

## Why it matters

Stale-blocked cards rot in the parked column when they could be
worked. Orphan-blocked cards lie to every graph walker — `pull-card`
treats them as terminal leaves with no upstream story, `next-card`
mis-prioritizes their downstream, and `goc triage` shows them parked
without surfacing what the human actually needs to decide. Cascade
chains hide the fact that one decision at the root unparks an entire
fan-out of work; without surfacing the root, the human picks at
leaves instead of pulling the cord that matters (Lean Andon).

## Fix

Add `validate_blocker_coherence(cards) -> list[Warning]` next to the
existing `validate_bidirectional_edges` in `goc/engine.py`. Three
warning classes, all non-fatal:

1. **`STALE_BLOCKED`** — `status: blocked` AND `advanced_by` non-empty
   AND every entry in `TERMINAL_STATUSES` (`done`, `superseded`,
   `disproved`). The card likely wants `status: open` or a refreshed
   blocker list.

2. **`ORPHAN_BLOCKED`** — `status: blocked` AND `advanced_by` empty
   AND `human_gate == "none"`. The real blocker is body-only; either
   hoist to `advanced_by`, raise the gate to claim the lock, or
   unflip the status. The suppression generalizes Option B to any
   raised gate (decision or session): a raised gate already names the
   bottleneck, so the orphan warning would be noise.

3. **`CASCADE_CHAIN_ROOT`** — when ≥3 blocked cards transitively reach
   the same `human_gate: decision` card via `advanced_by`, emit the
   warning against that decision card with the cluster size. One
   human decision cascade-unblocks the chain.

Wire into `_cmd_validate` after the existing checks. Print each
warning as `WARN <CLASS> <card>: <detail>` on stderr; warnings do NOT
contribute to the `errors` list or the non-zero exit. That keeps
`validate` usable as a strict CI gate while the warnings flow into
human triage.

## Cluster-park decision (Option B)

The user's spec proposed two options for `mutual-park` sibling
clusters where each card cites the other as a blocker:

- **Option A** — add a `parked_with: [other-card-slug, ...]` field for
  cluster siblings (non-directional, no DAG constraint).
- **Option B** — document that `human_gate: decision` + body-only
  references is the canonical pattern for mutual-park clusters; teach
  the validator to skip ORPHAN_BLOCKED warnings when
  `human_gate: decision` is set.

This card adopts **Option B**. Rationale: the cluster's bottleneck IS
a human decision (which member resolves first), and `human_gate`
already names that. A new schema field for one workaround pattern is
extra surface area; suppression on an existing gate value is zero
additional schema. The CASCADE_CHAIN_ROOT warning gives the human the
exact signal Option A was supposed to provide (here is the cluster, N
cards strong, here is the decision that unparks it).

## Implementation note

`validate_blocker_coherence` lives next to `validate_bidirectional_edges`
in `goc/engine.py`. `_cmd_validate` calls it after the existing
checks, prints warnings, and does NOT add them to `errors`. A new
test file `tests/test_validate_blocker_coherence.py` covers the three
classes plus the ORPHAN_BLOCKED-suppression case using the
temporary-deck pattern from `tests/test_repair_edges.py`.

---
title: mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
status: open
stage: null
contribution: medium
created: "2026-06-25T01:36:42Z"
closed_at: null
human_gate: none
advances: []
advanced_by:
  - goc-advance-claims-success-when-adding-an-already-existing-edge
  - goc-unadvance-claims-success-when-removing-a-non-existent-edge
  - goc-unadvance-with-self-target-leaves-card-in-half-edge-state
  - goc-decide-accepts-empty-decision-and-because-arguments
  - goc-attest-silently-ignores-unknown-skip-names
  - goc-status-silently-drops-worker-overrides-on-non-active-transitions
  - goc-wait-clear-silently-discards-reason-and-until-set-in-same-call
  - goc-status-superseded-discards-by-override-when-target-already-superseded
tags: [epic, meta-fix, api-contract]
summary: "Aggregation epic for a family of `goc` mutation verbs that accept redundant, empty, conflicting, or otherwise invalid input and — instead of rejecting it — perform a misleading no-op or silently drop the input, reporting exit 0 / a success line. Eight open sibling cards (filed 2026-05-29..06-22, each carrying its own `human_gate: decision`) share this shape across `advance`, `unadvance`, `decide`, `attest`, `status`, and `wait`. They cross-referenced each other in prose (the `goc <verb> accepts unwanted input` family named in `goc-decide-accepts-empty…`) but carried no schema edges, so the family was invisible to the scheduler/record axes and recurred as zero-edge `meta-fix` noise in every refine-deck orphan-dependency pass. Distinct from the `terminal-status-guard-missing-across-mutation-verbs` epic, which targets mutation of cards whose *status* is terminal regardless of input validity."
definition_of_done: |
  - [ ] PROCESS: A shared validation-failure shape is decided and recorded in this card's `log.md` — strict-refuse (exit 2, no mutation) vs. exit-0-with-stderr-WARNING vs. distinct no-op success message — and whether a reusable helper or per-verb inline checks are the right factoring. Note that the two no-op-success siblings (`advance`/`unadvance` redundant edge) explicitly want one shape applied to BOTH directions symmetrically.
  - [ ] PROCESS: All eight open child cards are closed or superseded under the agreed shape; this epic's `advanced_by` roster is all terminal.
  - [ ] TDD: A regression test asserts each guarded verb rejects (or honestly signals the no-op for) its invalid-input case — redundant edge add/remove, self-target unadvance, empty `--decision`/`--because`, unknown `--skip` name, worker-override on a non-active transition, `--clear` combined with `--reason`/`--until`, and `--by` on an already-superseded target.
  - [ ] MECHANICAL: `uv run goc validate` clean and `uv run python -m unittest discover -s tests` green after each child closes.
worker: {who: "claude[bot]", where: main}
---

# Mutation verbs accept invalid input and report a misleading no-op success

## What this epic coordinates

A family of `goc` mutation verbs share one root-cause shape: the
argparse layer accepts an input that is **redundant, empty, conflicting,
or otherwise invalid**, and the command function then performs a
misleading **no-op** or silently drops the input rather than rejecting
it — exiting 0 with a confident success line. The user (or a script
driving `--commit`) is left believing a mutation happened when none did,
or believing their input took effect when it was discarded.

This is the input-validation analogue of
[terminal-status-guard-missing-across-mutation-verbs](../terminal-status-guard-missing-across-mutation-verbs/):
that epic targets verbs that mutate a card whose *status* is already
terminal; this one targets verbs that accept *invalid input* regardless
of the target's status. The two families overlap conceptually (both are
"missing a precondition guard") but are disjoint in their cards and in
their fix: a terminal-status guard checks `card.status`, an
input-validation guard checks the *arguments*.

## Family roster (open children, wired via `advanced_by`)

Each is one CLI verb whose argparse layer accepts the input and whose
command function performs (or skips) the mutation without a precondition
check:

- [goc-advance-claims-success-when-adding-an-already-existing-edge](../goc-advance-claims-success-when-adding-an-already-existing-edge/) — `advance` reports `advanced_by += B` and exits 0 when the bidirectional edge already exists; the READMEs are rewritten byte-for-byte unchanged.
- [goc-unadvance-claims-success-when-removing-a-non-existent-edge](../goc-unadvance-claims-success-when-removing-a-non-existent-edge/) — the symmetric counterpart in the remove direction; reports a removal that never happened. The two no-op-success cards explicitly want one fix applied to both directions.
- [goc-unadvance-with-self-target-leaves-card-in-half-edge-state](../goc-unadvance-with-self-target-leaves-card-in-half-edge-state/) — `unadvance <t> --by <t>` accepts a self-target that `advance` already rejects; the missing guard in `_cmd_unadvance` can leave a half-edge state.
- [goc-decide-accepts-empty-decision-and-because-arguments](../goc-decide-accepts-empty-decision-and-because-arguments/) — `decide --decision '' --because ''` lowers the gate to `none` and writes a corrupt empty `## Decision` block, forging the Andon-cord handoff.
- [goc-attest-silently-ignores-unknown-skip-names](../goc-attest-silently-ignores-unknown-skip-names/) — `attest --skip <name>` accepts arbitrary strings; a typo is silently a no-op, so the user thinks a check was skipped when it actually ran.
- [goc-status-silently-drops-worker-overrides-on-non-active-transitions](../goc-status-silently-drops-worker-overrides-on-non-active-transitions/) — `--worker-who`/`--worker-where` are read only inside the `active` branch, so they silently produce no mutation on `open`/`disproved`/`superseded` transitions.
- [goc-wait-clear-silently-discards-reason-and-until-set-in-same-call](../goc-wait-clear-silently-discards-reason-and-until-set-in-same-call/) — `wait --clear --reason X --until Y` clears the overlay and silently discards the requested set; the mode conflict is accepted without rejection.
- [goc-status-superseded-discards-by-override-when-target-already-superseded](../goc-status-superseded-discards-by-override-when-target-already-superseded/) — `status <t> superseded --by <new>` early-returns when `prior == new_status`, before the `_mutate_pair` that wires the new typed forward routing, so a re-pointing `--by` is silently dropped.

## Why it matters

A misleading success is worse than an honest failure: it defeats the
scripts and agents that drive these verbs with `--commit` and trust the
exit code, and it corrupts the record axis (an empty `## Decision`
block, a check the user believes was skipped, a worker attribution that
never landed). Fixing the eight one at a time re-derives the same
"validate the argument before mutating" shape eight times and lets it
drift between verbs — exactly the meta-fix smell. This epic exists so
the family is resolved under one decision about the shared
validation-failure shape.

## How this card was surfaced

A `refine-deck` orphaned-dependency pass on 2026-06-25 found these eight
`meta-fix`-tagged cards carrying zero schema edges while cross-referencing
each other in prose as the "`goc <verb> accepts unwanted input`" family
(named explicitly in `goc-decide-accepts-empty-decision-and-because-arguments`).
Edge absence is invisible to `goc validate` (it enforces only edge
*symmetry*), so the family was invisible to the scheduler and the board's
dependency display, and it recurred as orphan-check noise every pass. The
parallel `terminal-status-guard-missing-across-mutation-verbs` umbrella
already consumed the *terminal-status* slice of the broader "missing
precondition guard" pattern; this card consumes the *input-validation*
slice.

## Scope notes

- The eight children each carry their own `human_gate: decision` with a
  per-verb option menu; those catalogues stay in each child's body. This
  epic is filed at `human_gate: none` by an autonomous refine-deck pass
  with no human in the loop — the wiring and framing are mechanical
  record/scheduler-axis hygiene, not a taste call. A future reader may
  raise this epic's gate to `decision` and record the shared-shape bundle
  (mirroring how `terminal-status-guard…` consolidated its children's
  recommendations) before authorising a single implementation series.
- Other zero-edge `meta-fix` cards surfaced in the same pass
  (`goc-migrate-list-style-leaves-bulk-rewrite-uncommitted`,
  `goc-decide-leaves-prior-decision-block-when-the-body-already-has-one`,
  `goc-upgrade-*`, `validate-backwards-epic-edge-fix-suggestion…`,
  `pattern-generalization-mutation-detector…`, etc.) are single-site
  defects with distinct root causes, not members of this family, and are
  correctly left unwired (per the verdict recorded in the closed
  [meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired](../meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired/):
  a single-site defect with no prose roster carrying zero edges is not
  rot).

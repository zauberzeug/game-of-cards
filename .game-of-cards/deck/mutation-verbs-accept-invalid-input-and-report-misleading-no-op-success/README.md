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
  - goc-wait-with-a-past-until-date-leaves-the-card-in-the-queue
tags: [epic, meta-fix, api-contract]
summary: "Aggregation epic for a family of `goc` mutation verbs that accept redundant, empty, conflicting, or otherwise invalid input and — instead of rejecting it — perform a misleading no-op or silently drop the input, reporting exit 0 / a success line. Nine sibling cards (filed 2026-05-29..2026-08-26, each filed at `human_gate: decision`) share this shape across `advance`, `unadvance`, `decide`, `attest`, `status`, and `wait`. They cross-referenced each other in prose (the `goc <verb> accepts unwanted input` family named in `goc-decide-accepts-empty…`) but carried no schema edges, so the family was invisible to the scheduler/record axes and recurred as zero-edge `meta-fix` noise in every refine-deck orphan-dependency pass. Distinct from the `terminal-status-guard-missing-across-mutation-verbs` epic, which targets mutation of cards whose *status* is terminal regardless of input validity."
definition_of_done: |
  - [x] PROCESS: A shared validation-failure shape is decided and recorded in this card's `log.md` — strict-refuse (exit 2, no mutation) vs. exit-0-with-stderr-WARNING vs. distinct no-op success message — and whether a reusable helper or per-verb inline checks are the right factoring. Note that the two no-op-success siblings (`advance`/`unadvance` redundant edge) explicitly want one shape applied to BOTH directions symmetrically. — decided 2026-10-22: 1. Strict-refuse with a one-line shared emission helper and per-verb predicates.
  - [ ] PROCESS: All nine open child cards are closed or superseded under the agreed shape; this epic's `advanced_by` roster is all terminal.
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

## Decision

*Resolved 2026-10-22T05:20:21Z:* 1. Strict-refuse: invalid input exits 2 with a goc error on stderr and mutates nothing; factoring per the card's recommendation, a one-line shared helper for the message and exit with the precondition predicates inline per verb

*Reasoning:* The maintainer accepted the card's recommendation in a human session on 2026-10-22; strict-refuse is the precondition-failure shape the engine already uses (exit 2) and the only one that protects --commit-driven scripts and agents

### How the decision reached the children

Five children asked exactly the shape question this card decided, so they carry a "Decided via parent" record and are pullable at `human_gate: none`: the redundant-edge pair (`goc-advance-claims-success-…`, `goc-unadvance-claims-success-…`), `goc-decide-accepts-empty-…`, `goc-attest-silently-ignores-unknown-skip-names` and `goc-wait-with-a-past-until-date-…`.

Four stay gated, because each asks a question the shape does not settle:

- `goc-unadvance-with-self-target-leaves-card-in-half-edge-state` — whether the guard sits in `_cmd_unadvance` (Option A) or inside `_mutate_pair` so that other callers such as `repair-edges` are covered too (Option B).
- `goc-status-silently-drops-worker-overrides-on-non-active-transitions` — whether the worker overrides should be honored on every transition (Option A) or refused (Option B).
- `goc-wait-clear-silently-discards-reason-and-until-set-in-same-call` — whether `--clear` combined with a set is refused (Option A) or means clear-then-set (Option B).
- `goc-status-superseded-discards-by-override-when-target-already-superseded` — whether a second `--by` redirects the supersession (option 1) or is refused (option 2).

If one of them is answered with "refuse", strict-refuse applies, with this card's shared emission helper.

That helper is `engine._refuse_invalid_input(reason)`, landed 2026-10-28 with `goc-unadvance-claims-success-…`: it prints `ERROR: <reason>` — the prefix every mutation verb's precondition refusal already used — and exits 2, so each child adds only its verb's predicate, called ahead of every write. The family's regression tests live in `tests/test_mutation_verbs_refuse_invalid_input.py`; each child adds its verb's cases there.

## Family roster (children, wired via `advanced_by`)

Each is one CLI verb whose argparse layer accepts the input and whose
command function performs (or skips) the mutation without a precondition
check:

- [goc-advance-claims-success-when-adding-an-already-existing-edge](../goc-advance-claims-success-when-adding-an-already-existing-edge/) — `advance` reports `advanced_by += B` and exits 0 when the bidirectional edge already exists; the READMEs are rewritten byte-for-byte unchanged.
- [goc-unadvance-claims-success-when-removing-a-non-existent-edge](../goc-unadvance-claims-success-when-removing-a-non-existent-edge/) — the symmetric counterpart in the remove direction; reported a removal that never happened. The two no-op-success cards explicitly want one fix applied to both directions. **Closed 2026-10-28**: `_cmd_unadvance` refuses when neither half of the edge is listed (and names the reversed command when the edge runs the other way); introduced the shared helper — `_cmd_advance`'s self-edge and cycle refusals route through it too — and the test module the other children extend.
- [goc-unadvance-with-self-target-leaves-card-in-half-edge-state](../goc-unadvance-with-self-target-leaves-card-in-half-edge-state/) — `unadvance <t> --by <t>` accepts a self-target that `advance` already rejects; the missing guard in `_cmd_unadvance` can leave a half-edge state.
- [goc-decide-accepts-empty-decision-and-because-arguments](../goc-decide-accepts-empty-decision-and-because-arguments/) — `decide --decision '' --because ''` lowers the gate to `none` and writes a corrupt empty `## Decision` block, forging the Andon-cord handoff.
- [goc-attest-silently-ignores-unknown-skip-names](../goc-attest-silently-ignores-unknown-skip-names/) — `attest --skip <name>` accepts arbitrary strings; a typo is silently a no-op, so the user thinks a check was skipped when it actually ran.
- [goc-status-silently-drops-worker-overrides-on-non-active-transitions](../goc-status-silently-drops-worker-overrides-on-non-active-transitions/) — `--worker-who`/`--worker-where` are read only inside the `active` branch, so they silently produce no mutation on `open`/`disproved`/`superseded` transitions.
- [goc-wait-clear-silently-discards-reason-and-until-set-in-same-call](../goc-wait-clear-silently-discards-reason-and-until-set-in-same-call/) — `wait --clear --reason X --until Y` clears the overlay and silently discards the requested set; the mode conflict is accepted without rejection.
- [goc-status-superseded-discards-by-override-when-target-already-superseded](../goc-status-superseded-discards-by-override-when-target-already-superseded/) — `status <t> superseded --by <new>` early-returns when `prior == new_status`, before the `_mutate_pair` that wires the new typed forward routing, so a re-pointing `--by` is silently dropped.
- [goc-wait-with-a-past-until-date-leaves-the-card-in-the-queue](../goc-wait-with-a-past-until-date-leaves-the-card-in-the-queue/) — `wait --until <date already past>` writes an overlay the engine's own read guard treats as non-impeding, then reports it exactly like a wait that took effect; the card stays in `--ready` and the next autonomous pull claims it.

## Why it matters

A misleading success is worse than an honest failure: it defeats the
scripts and agents that drive these verbs with `--commit` and trust the
exit code, and it corrupts the record axis (an empty `## Decision`
block, a check the user believes was skipped, a worker attribution that
never landed). Fixing the nine one at a time re-derives the same
"validate the argument before mutating" shape nine times and lets it
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

- The nine children each carry their own `human_gate: decision` with a
  per-verb option menu; those catalogues stay in each child's body. This
  epic was filed at `human_gate: none` by an autonomous refine-deck pass
  (the wiring and framing were mechanical record/scheduler-axis hygiene,
  not a taste call); a 2026-06-25 pull-card pass then raised the gate to
  `decision` to record the shared-shape bundle — mirroring how
  `terminal-status-guard…` consolidated its children's recommendations —
  before authorising a single implementation series. See `## Decision
  required` above for the bundle.
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
- **Adjacent, deliberately NOT a child:**
  [failed-auto-commit-leaves-card-files-staged-in-the-shared-git-index](../failed-auto-commit-leaves-card-files-staged-in-the-shared-git-index/)
  shares the visible symptom — a mutation verb prints its success line and
  exits 0 when its effect did not land — but its cause is an *environmental*
  failure (`git commit` rejected by a pre-commit hook), not input this epic's
  verbs should have refused. There is nothing to validate: the arguments are
  well-formed. Wiring it into `advanced_by` would make this epic's second DoD
  item ("All nine open child cards are closed…") false and would put a case
  with no invalid input under a shared input-validation shape. Recorded here
  so a future triage pass recognises it as already-considered rather than
  re-filing it as another child.

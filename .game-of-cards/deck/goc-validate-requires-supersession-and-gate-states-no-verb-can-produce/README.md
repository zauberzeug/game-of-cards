---
title: goc-validate-requires-supersession-and-gate-states-no-verb-can-produce
summary: "`goc validate` enforces two card-state invariants that no `goc` verb can produce a passing value for, so an affected card fails validation permanently. (1) A `superseded` card needs non-empty `superseded_by`, but `validate_superseded_by_targets` rejects any target that is itself terminal AND `_cmd_status` refuses to write a terminal `--by` — so a card whose genuine successor is done/superseded can never validate. The close-time guard `_enforce_no_inbound_superseded_by_or_exit` compounds it: the successor of ANY supersession can never be closed via `goc done`. (2) A terminal card requires `human_gate: none`, but `_cmd_decide` (the only gate-lowering verb) refuses terminal cards — so a card that reached terminal carrying a raised gate (old closure, hand-edit, migrate) fails validate forever with no repair path. Both contradict the shipped AGENTS.md record-axis contract: integrity is enforced 'regardless of either endpoint's status'."
status: done
stage: null
contribution: high
created: "2026-05-31T07:02:15Z"
closed_at: "2026-05-31T08:52:36Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: `deck/<title>/reproduce.py` exits zero — it asserts (a) `goc status <X> superseded --by <Y>` SUCCEEDS when `<Y>` is terminal, (b) the successor of a supersession can be closed via `goc done`, and (c) `goc decide` lowers a raised gate on a terminal card. Exits non-zero on current `main`.
  - [x] MECHANICAL: `validate_superseded_by_targets` no longer errors on a terminal `superseded_by` target (relaxed to referential-integrity only); the symmetric `validate_supersedes_targets` (target-must-be-superseded) is unchanged and still correct.
  - [x] MECHANICAL: the set-time `--by` terminal-successor guard in `_cmd_status` is removed; `--by` still requires the target to exist, not be self, and not form a cycle.
  - [x] MECHANICAL: the close-time guard `_enforce_no_inbound_superseded_by_or_exit` (and its helper `_inbound_superseded_by_holders`, if otherwise unused) is removed from all three call sites (`goc done`, `goc done --bundle`, `goc status` into terminal); completing the successor of a supersession is allowed.
  - [x] MECHANICAL: `_cmd_decide` lowers a still-raised gate on a terminal card (repair path); it still refuses when the gate is already `none`. The success/log output reflects post-closure repair for terminal cards rather than falsely promising the card is pullable.
  - [x] TDD: the three regression tests that locked in the old behavior (`test_superseded_by_must_be_live`, `test_close_with_inbound_superseded_by`, `test_decide_terminal_status_guard`) are rewritten to assert the corrected behavior; `test_close_terminal_gate_guard` (validator still rejects terminal+gate-raised; close paths still refuse to CREATE that state) stays green unchanged.
  - [x] PROCESS: amend the two closed origin cards (`goc-status-superseded-by-accepts-terminal-status-successor`, `goc-decide-accepts-decisions-on-already-closed-cards`) and the close-time-guard card (`closing-a-card-with-inbound-superseded-by-creates-dead-end-routing`) with a dated `log.md` forward pointer to this card; note the `goc-done-marks-cards-done-without-clearing-or-checking-human-gate` relationship in this card's log.
  - [x] MECHANICAL: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; plugin mirrors regenerated (`python scripts/sync_plugin_assets.py`); `pre-commit run --all-files` clean.
worker: {who: Rodja Trappe, where: main}
---

# `goc validate` requires supersession + gate states no verb can produce

A downstream consumer (goc 0.0.22) reported two states where `goc
validate` demands a value that no `goc` verb can write — the affected
card then fails validation permanently, with hand-editing also blocked
because the validator rejects the only legal target.

## Bug 1 — supersession lineage to a terminal successor is unrepresentable

Three guards, added across three earlier cards, jointly enforce a
"`superseded_by` must always point at *live* work" invariant:

- `validate_card` requires non-empty `superseded_by` on every
  `superseded` card (`engine.py` ~1358).
- `validate_superseded_by_targets` (`engine.py` ~1412, wired at ~3170)
  rejects any `superseded_by` whose target is terminal.
- `_cmd_status` refuses to write a terminal `--by` successor
  (`engine.py` ~4282).
- `_enforce_no_inbound_superseded_by_or_exit` (`engine.py` ~1575, called
  from `goc done` ~3517, `goc done --bundle` ~3601, and `goc status`
  into terminal ~4320) refuses to close any card that another card
  routes forward to.

The combined effect is contradictory:

1. When a card's genuine successor is itself `done`/`superseded`, **no
   value** of `superseded_by` passes `goc validate` — and hand-editing
   can't help, because the validator rejects the terminal target.
2. Worse, `_enforce_no_inbound_superseded_by_or_exit` means the
   successor of *any* supersession can **never be completed**: you
   `goc status A superseded --by B` (B live), then `goc done B` is
   refused because `A.superseded_by` still points at B. The successor —
   the live work the supersession was created to track — is permanently
   un-closeable. The only way a supersession's successor becomes `done`
   today is by bypassing the verbs (hand-edit / migrate), which then
   trips `validate_superseded_by_targets`.

### Why the invariant is wrong

The schema's *documented* supersession invariants (see
`Skill(card-schema)` "Replacement axis") are only: bidirectional
consistency, `superseded_by`⇒`status: superseded`, and
`supersedes`⇒target-superseded. **None** require the `superseded_by`
target to be live. The "must be live" rule lives only in code — the
engine drifted *stricter* than its own contract.

`AGENTS.md` "Deck as scheduler vs deck as record" is explicit: the
record axis "walks edges that include closed cards… enforced regardless
of either endpoint's status." A forward walk that lands on a `done`
successor has not hit a dead end — it has reached the **resolution**
("the replacement was completed"). A `superseded` successor carries its
own `superseded_by`, so the walk continues. The walk always terminates
at `open`/`active` (live), `done` (resolved), or `disproved`/`superseded`
(abandoned/re-routed) — every terminus is informative.

### Fix

Relax the invariant from "target must be live" → "target must exist"
(referential integrity, already enforced generically for every
`LIST_REL_FIELD`): remove the set-time `--by` terminal guard, neuter the
terminal branch of `validate_superseded_by_targets`, and remove
`_enforce_no_inbound_superseded_by_or_exit` entirely. `validate_supersedes_targets`
(the *symmetric* check the report mentions) enforces a different and
still-correct rule — `supersedes` targets must be `status: superseded`
— and is left unchanged.

## Bug 2 — a terminal card with a raised gate cannot be repaired

`validate_card` requires `human_gate: none` once `status` is terminal
(`engine.py` ~1292). The close-time verbs correctly refuse to *create*
that state (they tell you to `goc decide` first). But `_cmd_decide` —
the only verb that lowers a gate — refuses terminal cards outright
(`engine.py` ~4904). No other verb writes `human_gate: none`
(`goc done --force` only bypasses DoD enforcement). So a card that
reached a terminal status while carrying a raised gate — via an older
closure that predates the close-time gate guard, a hand-edit, or a
`goc migrate` import — fails `goc validate` forever with no escape.

### Fix

Let `goc decide` lower a still-raised gate on a terminal card (the
repair path). Reorder the guards so the "gate already none" check runs
first — that already covers every *cleanly*-closed terminal card (they
all have `gate: none`), so the only terminal cards `decide` will touch
are precisely the broken ones that need repair. The success line and
`log.md` entry are made status-aware so a terminal repair does not
falsely announce the card is now pullable.

## Reachability

Both surface in practice because the close-time guards only fire on
transitions made *through those verbs after the guard shipped*. Older
closures, hand-edits, `goc migrate` imports, and supersessions whose
successor later closed all land in the contradictory state — and once
there, no verb can move them back to a validating shape.

## Empirical evidence

`uv run python deck/<title>/reproduce.py` on current `main` exits
non-zero: superseding by a terminal `--by` is refused, the successor of
a supersession cannot be `goc done`, and `goc decide` refuses a terminal
card with a raised gate. After the fix, all three succeed and the script
exits zero.

## Closure-is-not-frozenness note

This card reverses guards landed by three closed cards
(`goc-status-superseded-by-accepts-terminal-status-successor`,
`closing-a-card-with-inbound-superseded-by-creates-dead-end-routing`,
`goc-decide-accepts-decisions-on-already-closed-cards`). Those cards
reasoned from "routes forward presupposes a live destination" and missed
that a completed successor is the resolution, not a graveyard. Each gets
a dated forward pointer in its `log.md`.

This bug is the gate-vs-terminal-status family member that completes the
arc begun by `goc-done-marks-cards-done-without-clearing-or-checking-human-gate`
(which added the close-time gate guard so the contradictory state can no
longer be *created*) and `goc-decide-accepts-decisions-on-already-closed-cards`
(which over-corrected into refusing the *repair*). The close-time guard
stays; this card restores the repair path so the validator's invariant is
satisfiable, not just enforced.

## Deck hygiene performed alongside the fix

The fix exposed that this repo's own deck already carried the very states
the bugs describe — `goc validate` was red on `main` with 7 errors (the
autonomous puller bypasses pre-commit, see
`pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate`).
The engine fix alone cleared one (a real Bug-1 instance: a `superseded`
card whose `superseded_by` pointed at a `done` card). The remaining 6 were
repaired as part of this card (Rodja opted into a full hygiene pass):

- `install-openclaw-harness`, `make-claude-md-and-agents-md-merge-opt-in-via-skill`,
  `publish-game-of-cards-agent-plugins` — `superseded` with empty
  `superseded_by`. Successors recovered from each card's `log.md`/body and
  wired (`superseded_by` added by hand because `goc status … superseded --by`
  no-ops on an already-superseded card — separate open bug
  `goc-status-superseded-discards-by-override-when-target-already-superseded`;
  inverse `supersedes` filled by `goc repair-edges --apply`). The publish
  card was a 1→3 split, so it routes forward to all three per-runtime
  publish cards.
- `make-claude-md-…` (session gate) and `rename-blocks-to-advances-and-design-value-sort`
  (session gate on a `done` card) — stale gates cleared via the new
  `goc decide` repair path, dogfooding Bug 2's fix on real data.
- One pre-existing advances half-edge — fixed by `goc repair-edges --apply`.

`goc validate` is now green (exit 0).

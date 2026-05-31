---
title: validate-flags-card-states-that-no-verb-can-repair
summary: "Generalization (spawned by `goc-validate-requires-supersession-and-gate-states-no-verb-can-produce`): `goc validate` enforces several frontmatter invariants for which no CLI verb can *repair* an offending card once it lands in the bad state. Two were just fixed (terminal `superseded_by` target; raised gate on a terminal card), but the shape recurs — other terminal-state invariants (e.g. `closed_at` set-iff-terminal, `superseded`⇒non-empty `superseded_by`) are only ever written by the close verbs, so a card that reaches the bad state via a hand-edit, a `goc migrate` import, or a bot commit that bypassed pre-commit has no repair path but `git`. The repair gap is systemic because the autonomous puller bypasses the pre-commit `goc validate` gate (`pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate`), so validator-red states accumulate on `main` silently. `goc repair-edges` is the lone proof that the repair-verb pattern is already valued — it just isn't generalized."
status: open
stage: null
contribution: medium
created: "2026-05-31T08:58:10Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [meta-fix, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` — pick scope: (a) audit-only (enumerate every `goc validate` invariant and confirm a producing+repairing verb path exists, file per-gap cards), (b) extend `goc repair-edges` into a general `goc repair [--apply]` that fixes every *mechanically* repairable validator violation (half-edges, missing `closed_at`, etc.) and names the ones needing human judgment, or (c) a hybrid.
  - [ ] MECHANICAL: enumerate the `goc validate` invariants (engine.py `validate_card` + the `validate_*` / `detect_*` functions) and, for each, record whether a non-`git` verb can both *produce* and *repair* the valid state. The enumeration is the deliverable regardless of which fix path is chosen.
  - [ ] TDD: for each invariant the decision says should be repairable, a regression test asserts the repair verb takes a card from the validator-red state to green without reopening or otherwise corrupting it (model on `tests/test_decide_repairs_terminal_gate.py`).
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# `goc validate` flags card states that no verb can repair

## The pattern

`goc validate` is the deck's frontmatter contract enforcer. But enforcing
an invariant is only sound if a CLI verb can both **produce** a passing
value and **repair** a card that has drifted into a violating state. When
the only writer of a required field is a verb that *refuses* the very cards
that need fixing, the invariant becomes a permanent red with no escape but
hand-editing through `git`.

This card generalizes
[`goc-validate-requires-supersession-and-gate-states-no-verb-can-produce`](../goc-validate-requires-supersession-and-gate-states-no-verb-can-produce/),
which fixed two instances of exactly this shape:

- **terminal `superseded_by` target** — the validator demanded a live
  target the verbs refused to write (fixed by relaxing the invariant).
- **raised gate on a terminal card** — the validator demanded
  `human_gate: none`, but `goc decide` (the only gate-lowering verb)
  refused terminal cards (fixed by making `decide` the repair verb).

One was fixed by *relaxing the invariant*, the other by *adding a repair
path* — which is exactly why the general question ("for each invariant,
relax or add a repair verb?") deserves its own audit rather than being
answered ad hoc per bug report.

## Why it recurs

Several `goc validate` invariants are written *only* by the close-time
verbs (`goc done`, `goc done --bundle`, `goc status … <terminal>`):

- `closed_at` must be set iff `status` is terminal.
- `status: superseded` ⇒ non-empty `superseded_by`.
- `human_gate: none` once terminal.

A card can reach a violating combination of these via a route the close
verbs never policed:

1. **Hand-edits** to frontmatter.
2. **`goc migrate`** imports of legacy decks.
3. **Autonomous bot commits** — the puller bypasses the pre-commit
   `goc validate` gate
   ([`pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate`](../pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate/)),
   so a card it writes in a red state lands on `main` unchecked.

The hygiene pass on the parent card was empirical proof: this repo's own
deck was carrying six validator-red states on `main`, several of which had
**no repair verb** — `superseded_by` had to be hand-edited because
`goc status … superseded --by` no-ops on an already-superseded card
([`goc-status-superseded-discards-by-override-when-target-already-superseded`](../goc-status-superseded-discards-by-override-when-target-already-superseded/)).

## The existing template

`goc repair-edges [--apply]` already embodies the pattern for the
relationship graph: it detects half-edges and writes the missing reverse
side. The generalization is to (a) confirm every other invariant has a
comparable repair path, and (b) decide whether the mechanically-repairable
ones deserve a single `goc repair` umbrella verb rather than one bespoke
repair affordance per invariant.

## Not in scope

Closing the bot-bypass hole itself — that is the separate open card
`pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate`.
This card is about ensuring that *when* a red state lands (by any route),
the operator has a verb to fix it.

## Decision required

Pick the scope before implementing (see DoD PROCESS item):

1. **Audit-only** — enumerate the invariants and the producing/repairing
   verb for each; file a per-gap card where no repair verb exists. Cheapest;
   defers the build.
2. **General `goc repair`** — extend `repair-edges` into a `goc repair
   [--apply]` that fixes every mechanically-repairable violation and lists
   the judgment-needing ones. Most user value; largest build.
3. **Hybrid** — audit now, build `goc repair` incrementally as gaps are
   confirmed.

---
title: advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose
summary: |-
  `advanced-by-closed` (and the about-to-land derived dependency-
  readiness) treat EVERY `advanced_by` edge as a hard
  closure/readiness prerequisite. But the design card
  `rename-blocks-to-advances-and-design-value-sort` defines the edge as
  "~80% value contribution, ~20% strict prerequisite," with the
  strict/loose distinction "carried by the body, not the field." So the
  hard reading over-reads the loose majority: in a densely-linked deck,
  aggregator-epics with `advanced_by` up to 24 are each held closed
  until every contributor closes, even where an edge means "this
  informed that," not "this blocks that." DECIDED (2026-05-26): the
  closure gate is correct as-is — "X advances Y" means Y's value chain
  includes X, so a true edge ⇔ Y not done; if Y can close, the edge was
  false and must be retracted (Option E). The loose/strict distinction
  governs *start ordering*, not closure, so the genuine over-read lives
  in derived *readiness*, delegated to the epic's children. This card
  now carries the Option E closure work; gate lowered to none.
status: done
stage: null
contribution: high
created: "2026-05-26T04:55:34Z"
closed_at: 2026-05-26T05:42:28Z
human_gate: none
advances:
  - blocked-status-conflates-dependency-external-wait-and-deferral
advanced_by: []
tags: [api-contract, documentation]
definition_of_done: |
  - [x] Option chosen and recorded (`## Decision`, 2026-05-26); gate
        lowered to `none`. Closure half = Option E; readiness half
        delegated to the epic's children.
  - [x] `card-schema` reaffirms `advanced-by-closed` is *correct*, with
        the value-chain rule ("X advances Y" ⇔ Y's value chain includes
        X ⇔ Y not done while X open) and the closure-vs-readiness
        asymmetry table (loose edges block closure but not start order).
  - [x] `advanced-by-closed`'s failure message names the two honest
        resolutions — wait, or `goc unadvance <closing> --by <upstream>`
        (documented on both cards) when the edge is discovered false —
        and `finish-card` blesses retraction over `--skip` as the
        first-line escape.
  - [x] `_run_derived_check`'s `advanced-by-closed` logic is left
        unchanged (no severity downgrade, no per-edge marker); the work
        is messaging + docs only. `goc validate` stays green.
  - [x] reproduce.py: closing `C` with a true open `advanced_by` edge
        FAILs; `goc unadvance C --by P` (edge was false) then lets it
        close. Loose-vs-strict is a readiness concern, tested there.
  - [x] The readiness half is handed off: the `derive-dependency-
        readiness-…` child is amended with the closure-vs-readiness
        asymmetry so its `dependency_blocked` predicate doesn't inherit
        the closure reading. This card does NOT implement readiness.
worker: {who: "claude[bot]", where: main}
---

# `advanced_by` is read as a hard prerequisite, but documented as mostly a loose contribution

## Origin

Second-pass report from a contributor running goc 0.0.20, after the
first report's `advanced-by-closed`-is-buggy framing was corrected. The
check is *mechanically* correct; this card is about the semantics it
assumes. Split out from the authoring/lint guardrail
[`no-guardrail-for-canonical-epic-edge-direction`](../no-guardrail-for-canonical-epic-edge-direction/),
which fixes the backwards-modeling problem and explicitly does **not**
touch the check.

## The tension

`advanced-by-closed` (`goc/engine.py` `_run_derived_check`) fails
closure of card `C` while any card in `C.advanced_by` is not `done` —
treating every `advanced_by` entry as a hard closure prerequisite. It
ships in the default config (`templates/game_of_cards/config.yaml`,
`layer_3_goc_dod`), so every adopter inherits it.

But the design card `rename-blocks-to-advances-and-design-value-sort`
deliberately defines `advances`/`advanced_by` as **~80% loose value
contribution, ~20% strict prerequisite**, and states the strict/loose
distinction "was always carried by the body, not the field" — the
schema-level distinction was *dropped on purpose* to stop `blocks`
reading adversarial. So the field genuinely cannot tell a hard
prerequisite from a loose "this informed that," yet `advanced-by-closed`
reads all of them as hard.

In a densely-linked deck this bites constantly. The contributor's
downstream deck has aggregator-epics with `advanced_by` of 24
(`a5-homeostat-unification`) and 19 (`kappa-readout-canonical-form`);
each is held closed until *every* contributor closes. Correct for a
true aggregation epic — wrong wherever the edge is a loose contribution.

## Decision (2026-05-26) — Option E (closure half); readiness delegated

The full A–D options matrix and the E-vs-B deliberation are archived in
`log.md`. The decision turned on one observation that dissolved the
framing, not on weighing the options as posed.

**The value-chain identity.** "X advances Y" is *defined* as "closing X
delivers a piece of Y's value chain" (`rename-blocks-to-advances`). It
follows that, for **closure**:

> a true `advances` edge ⇔ Y's value chain includes X ⇔ Y is **not
> done** while X is open.

There is no coherent "true edge you may close past." Either the edge is
true (so Y isn't done — the FAIL is correct), or Y is genuinely
closeable (so the edge was false and points at the wrong target — e.g.
"more tests for C" does not advance C; it advances *the testing of C's
functionality*, a different card). The earlier worry that a hard gate
blocks legitimate closures rested on a mis-modeled edge.

**Therefore `advanced-by-closed` is correct as-is — Option E.** Keep the
hard FAIL. The blessed resolution when you hit it is not `--skip`: it is
to **retract the false edge** — `goc unadvance <closing> --by <upstream>`,
documented on both cards — which is honest graph maintenance, not a
bypass. Options A–D are rejected: B/C/D all weaken a correct gate, and A
re-introduces the strict/loose schema split that was removed on purpose.

**The loose/strict distinction is real — but it governs *start
ordering*, not closure.** Loose ("X contributes; doesn't gate") means
you may *begin* Y before X is done; it does **not** mean Y can be
*declared done* with X's piece undelivered. So both loose and strict
true edges block closure; they differ only on whether work on Y may
start first:

| edge | may Y *start* before X done? | may Y *close* while X open? |
|---|---|---|
| strict (X required before Y begins) | no | no |
| loose (X contributes, no order) | **yes** | **no** (X is in Y's value chain) |

**Consequence — the real over-read is in *readiness*, not attest.** The
contributor's instinct (the hard reading over-fires on loose edges) is
correct, but it lands on the epic's `derive-dependency-readiness` child,
whose planned `dependency_blocked(card)` returns true for *any*
non-terminal `advanced_by` — which would wrongly block *starting* a card
on a loose edge. That is delegated to the epic's children
([`derive-dependency-readiness-…`](../derive-dependency-readiness-instead-of-storing-blocked-status/)
for the start-ordering question; [`add-waiting-overlay-…`](../add-waiting-overlay-with-reason-and-until-date/)
for hard human/external impediments). This card amends that child with
the asymmetry and does not implement readiness itself.

This card now carries only the Option E *closure* work (a messaging +
docs change; the check logic is unchanged). Gate lowered to `none`.

---
title: escalate-repeatedly-auto-released-cards-without-an-attempt-counter
summary: "An autonomous worker that claims a card and releases it without closing gets no core-level backstop, so the picker re-offers the same unclosable card indefinitely. Escalate via a two-rung waiting_on -> human_gate ladder on the release transition, deliberately without an attempt counter."
status: open
stage: null
contribution: medium
created: "2026-07-26T07:09:41Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
draft: true
definition_of_done: |
  - [ ] PROCESS: HELD AS DRAFT. Do not implement until `human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property` is decided — the ladder below escalates on release, and that card requires escalation to distinguish a productive pass from a no-op one. Reconcile, then publish or close as superseded.
  - [ ] MECHANICAL: the `active → open` release transition in `_cmd_status` (`goc/engine.py:5901`) applies rung 1 — set `waiting_on` (reason naming the auto-release) plus a near-future `waiting_until` — when the card is released without reaching a terminal status and carries no impediment overlay yet.
  - [ ] MECHANICAL: rung 2 — a release on a card whose `waiting_on` already carries the auto-release reason AND whose `waiting_until` has elapsed escalates `human_gate: none → session`, with the reason recorded in `log.md`. Escalation is terminal for the loop: `session` is already filtered by every ready/scheduler/triage predicate.
  - [ ] MECHANICAL: escalation fires ONLY for unattended releases. A human running `goc status <card> open` by hand must not arm the ladder — gate the behaviour on the autonomous path (worker identity or an explicit flag), not on the bare transition.
  - [ ] TDD: a regression test drives rung 1 → elapsed wait → rung 2 and asserts the gate lands on `session`; a sibling case asserts a card released once and then closed normally never escalates, and that a manual human release does not arm the ladder.
  - [ ] TDD: `tests/test_scheduler_workable_predicate_coupling.py` still passes — this card adds no new axis to the ready predicate (it reuses `waiting_impedes` and `human_gate`), and the test must confirm that rather than needing a new axis registered.
  - [ ] MECHANICAL: no new frontmatter field and no schema change. `goc validate` clean; if this card ever needs `release_count`, that is a re-litigation of the recorded decision and belongs in a new card.
  - [ ] MECHANICAL: docs updated — whichever of card-schema / pull-card / next-card / deck describes the `human_gate` lifecycle or the `waiting_on` overlay documents the ladder. Plugin mirrors synced.
---

# Escalate repeatedly auto-released cards without an attempt counter

> ⚠ **Held as a draft — known defect in the trigger.** This card's
> ladder escalates on *release without closure*, which cannot tell a
> pass that ticked boxes from one that did nothing.
> [`human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property`](../human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property/)
> requires exactly that distinction, and shows a downstream card with
> eight DoD items of which one is human-only — the ladder as specified
> would park it while seven items were still agent-workable. Decide that
> card first. The counter analysis below stands on its own; the trigger
> does not.

## Summary

When an autonomous worker claims a card and then releases it without
closing, `goc` itself does nothing. The card returns to the queue
unchanged, so the picker offers it again on the next pass — and again.
This card adds the core-level backstop: a **two-rung escalation ladder**
built from the existing `waiting_on` / `waiting_until` overlay, with
**no attempt counter** anywhere in the schema.

## Location

- `_cmd_status` — `goc/engine.py:5901` (the release transition to hook)
- `waiting_impedes` — `goc/engine.py:2696` (the overlay predicate reused)
- `validate_waiting_overlay` — `goc/engine.py:2236` (surfaces elapsed waits)
- `card_is_ready` — `goc/engine.py:2424` (unchanged by this card)

## What's broken

The ready predicate has no memory. `card_is_ready` gates on status,
draft, gate, and impediment — all *stored* state, none of it reflecting
that an agent already tried this card and gave up:

```python
if card.status != "open":      return False
if card.human_gate != "none":  return False
if waiting_impedes(card):      return False
return True
```

So a card that an unattended worker cannot finish — for any reason —
is re-offered indefinitely. Every consumer of the autonomous pull loop
has the same hole, and each one either hand-rolls a net or burns passes
forever.

## Evidence

Recorded on the parent card
[`autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`](../autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/):
a downstream `goc` consumer hit this repeatedly and grew its own
release-attempt counter in its drain wrapper. Before that counter
tripped, roughly two to three passes were spent re-pulling one card
whose DoD required a human. The net worked — but it lives in one
consumer's wrapper, so every other consumer still has none.

No `reproduce.py` ships with this card: reproducing the symptom
requires driving a full autonomous pull loop across sessions, which the
regression tests in the DoD simulate directly at the engine level
instead (drive the transitions, assert the rungs).

## Why it matters

The waste is silent. From the queue's point of view the card looks like
a normal top-value `none`-gated card, so the loop keeps selecting it and
the cost shows up only as unexplained token spend. Related but distinct:
[`trim-token-cost-of-autonomous-card-cycles`](../trim-token-cost-of-autonomous-card-cycles/)
attacks per-cycle cost; this card removes cycles that were never going
to produce anything.

The prevention half of the problem — cards whose DoD is *structurally*
human-only, detectable at authoring time — is the parent card's scope
(publish-time warning + a `goc validate` lint). This card is the
behavioural backstop underneath it: it does not care *why* the worker
could not finish, only that it demonstrably could not, twice.

## Fix — the two-rung ladder

Hook the `active → open` release transition the engine already mediates:

1. **Rung 1 — first unattended release without closure.** Set
   `waiting_on` with a reason naming the auto-release, plus a
   near-future `waiting_until`. The card leaves the queue immediately
   (every ready / scheduler / triage predicate already honours
   `waiting_impedes`), then **self-clears** when the date passes and
   returns to the queue on its own.
2. **Rung 2 — released again after that overlay elapsed.** Escalate
   `human_gate: none → session`, log the reason. Two *independent*
   failures, separated by a cooling-off period, is the evidence that the
   card is structurally unworkable unattended rather than transiently
   blocked.

The rung *is* the count: `none → waiting → session`. This works because
of a property `waiting_impedes` already documents (`goc/engine.py:2696`):

> *"When `waiting_until` is in the past (elapsed), the card RE-ENTERS
> the queue with no manual action — the elapsed-wait is then surfaced
> separately by `validate_waiting_overlay` as an SLE escalation
> signal."*

Self-clearing is what makes two rungs sufficient. A card blocked by a
transient condition recovers automatically and never reaches rung 2; only
a genuine repeat offender does.

## Why there is no attempt counter

Decided on the parent card (2026-07-26) and recorded here so it is not
re-litigated from scratch:

- **A frontmatter integer (`release_count: N`)** would be the first
  field written by the machine, for the machine, and meaningless to a
  human reading the card cold — unlike `status`, `human_gate`,
  `waiting_on`, `draft`, `worker`, `closed_at`. It also rewrites
  `README.md` frontmatter on every failed pull, concentrating commit
  churn and merge-conflict surface on the hottest file in the card,
  against AGENTS.md § Parallel-Agent Commit Safety — and costs a schema
  change plus migration for an advisory metric.
- **Counting `## ` headings in `log.md`** has partial precedent (the
  `log-md-closure-entry` derived check, `goc/engine.py:5649`), but that
  is a *presence check for one well-known heading at one decision
  point*, not a tally over an open vocabulary. Heading formats are
  already heterogeneous — `goc decide` writes `## {ts}: decision
  recorded`, `goc done` writes `## {ts} — Closure`, `goc move` writes
  `## {ts}: renamed from …`, and humans write free-form entries. A count
  would measure *how much has been written about the card* rather than
  *failed pulls*, escalating well-documented cards and missing real
  offenders. It would also make prose load-bearing: tidying the journal
  would silently change scheduler behaviour.

Revisit **only** on evidence that the fixed two-rung budget is wrong, or
if deck-wide telemetry on backstop firings becomes a real requirement; a
tunable `max_releases` in `.game-of-cards/config.yaml` is the migration
path if so.

## Scope boundary

- **Parent / sibling:**
  [`autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`](../autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/)
  owns the prevention half (publish-time warning + validate lint) and
  carries the decision record. No value-flow edge: neither card blocks
  the other, and they fix the same symptom through independent
  mechanisms — heuristic there, observed behaviour here.
- **Not the aggregation-epic head-block:**
  [`aggregation-epics-head-block-the-autonomous-pull-queue`](../aggregation-epics-head-block-the-autonomous-pull-queue/)
  shares the symptom but its root cause is a pure aggregator with no
  work of its own. This ladder would *also* contain that case, but it is
  containment, not the fix — keep the cards distinct.
- **Prior art for the overlay:**
  [`add-waiting-overlay-with-reason-and-until-date`](../add-waiting-overlay-with-reason-and-until-date/).

---
title: autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish
status: open
stage: null
contribution: medium
created: "2026-07-22T05:26:01Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: pick a mechanism from "## Decision required" (or a fifth) and record the choice + rationale here and in log.md.
  - [ ] MECHANICAL: implement the chosen mechanism so that a card whose DoD is *structurally human-only* no longer reaches an autonomous worker at `human_gate: none` unbounded — whether by detection at `goc new`, a `goc validate` warning, or a core-level auto-escalation after N releases. Touch `goc/engine.py` (and/or the `new`/`validate` paths) as the mechanism requires.
  - [ ] TDD: a regression test encodes the chosen behaviour — e.g. `goc validate` flags a `human_gate: none` open card whose DoD carries a human-only `EMPIRICAL:` item, and/or the release-escalation trips to `session` after the configured budget. The test must NOT regress cards with genuinely autonomous DoD.
  - [ ] MECHANICAL: docs updated — whichever of card-schema / create-card / next-card / pull-card / deck / AGENTS describes the ready-to-pull predicate, the `human_gate` lifecycle, or the DoD method-class tags reflects the new behaviour. Plugin mirrors synced; `uv run goc validate` clean.
---

# Autonomous picker wastes passes on cards only a human can finish

## What's broken

Some cards have a Definition of Done that is **structurally
completable only by a human** — not merely unprovisioned in one
worktree, but forever off-limits to an unattended agent. The canonical
shape is an `EMPIRICAL:` item that requires a human to trigger a live,
side-effecting action, or to verify behaviour on a physical device.
(This card originally cited the Zoe App card
`conversations-send-and-receive-file-attachments` as its concrete
instance. That was wrong, and the correction matters for scoping: only
one of that card's eight DoD items is human-only — a production send
plus a live-device file-picker check — and the rest is ordinary agent
work. It is a *mixed* card, and gating it earlier would have frozen the
agent-workable majority sooner. See
[`human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property`](../human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property/)
for that failure mode. This card's scope is the genuinely
**all-human-only** card; whatever mechanism it picks must not misfire on
mixed ones — in particular a lint keyed on "any `EMPIRICAL:` item
mentioning production or a device" would.)

Such a card is nonetheless born at `human_gate: none`, because nothing
inspects the DoD at creation. The autonomous picker's ready predicate
(`card_is_ready`, mirrored by `card_is_workable_for_scheduler`) gates
only on:

```python
if card.status != "open":      return False
if card.human_gate != "none":  return False
if waiting_impedes(card):      return False
return True
```

Nothing in that predicate accounts for "this card *has* actionable work,
but the work can only be executed or verified by a human." So
`pull-card` pulls it, a fresh agent spins up, reads a DoD it cannot
satisfy without a human, and exits without closing. The harness
re-triggers, the picker offers the same card again — **a wasted pull**,
repeated until a human (or a downstream safety net) raises the gate.

## Why it matters

Every such pull is burned compute and tokens on a foregone conclusion.
The waste is silent: from the queue's point of view the card is a
normal top-value `none`-gated card, so the loop keeps selecting it. The
correct end state (`human_gate: session`, which every ready/scheduler/
triage predicate already filters out — see
[`board-omits-pull-blocking-marker-for-human-gate-parked-cards`](../board-omits-pull-blocking-marker-for-human-gate-parked-cards/)
and its coupling invariant test) is reached only *reactively*, after N
passes have already been spent discovering it.

## Prior art — the downstream drain already patches this, in the wrong layer

The Zoe App autonomous loop (a downstream `goc` consumer) hit this
repeatedly and grew its own **release-attempt counter** as a safety net:
`_count_release_attempts` / `release_claim_if_stuck` in its
`tool/_lib.sh`. After a card is auto-released `max_releases` times
without a close, the wrapper runs the equivalent of `goc status … ` +
gate-raise and escalates it to `human_gate: session`, logging
`auto-released N× → gate:session for human triage`. Observed in the
wild: the attachments card above burned ~2–3 passes before this counter
tripped and parked it.

Two lessons for the core:

1. **The escalation net belongs in `goc`, not in each drain wrapper.**
   Every other consumer of the autonomous pull loop gets *no* net today —
   for them the wasted-pull cycle is bounded only by queue dynamics.
   A release-count → gate escalation implemented once in the engine (or
   the pull/next skills) would protect all consumers uniformly.
2. **A net is not prevention.** Even with the counter, the first N
   passes are still wasted. The DoD carried the signal all along —
   `EMPIRICAL:` items describing human-only actions — so the cheaper win
   is to *detect at creation* and never offer the card unattended in the
   first place.

## The building blocks already exist

- **DoD method-class tags.** `EMPIRICAL:` is a first-class DoD prefix and
  `goc validate` already has a warning-only `UNTAGGED_DOD_ITEM` class
  (see [`tag-dod-items-by-method-class-test-experiment-edit-or-decision`](../tag-dod-items-by-method-class-test-experiment-edit-or-decision/)).
  A "human-only DoD" lint would key off exactly this taxonomy.
- **The `human_gate` predicate cluster** with its documented coupling
  invariant and `tests/test_scheduler_workable_predicate_coupling.py`
  (a new axis added to one predicate must be added to all).
- **The `waiting_on` / `waiting_until` read-time guard**
  ([`add-waiting-overlay-with-reason-and-until-date`](../add-waiting-overlay-with-reason-and-until-date/))
  — prior art for "keep a card out of the queue without raising
  `human_gate`," should an escalation want a softer overlay than a hard
  gate flip.

## Scope boundary — not the aggregation-epics head-block

[`aggregation-epics-head-block-the-autonomous-pull-queue`](../aggregation-epics-head-block-the-autonomous-pull-queue/)
describes the *same symptom* (picker offers a card it cannot close →
wasted pull) but a **different root cause**: a pure-aggregator epic with
**no actionable work of its own**, closure-gated on unpullable children.
That card explicitly contrasts "has no actionable work at all" (its
case) against a card that *has* real work only a human can execute —
which is precisely this card. The two fixes may share machinery (both
touch the ready predicate) but the detection signal differs: child-gate
inheritance there, DoD method-class here. Keep them distinct; cross-link
resolutions.

## Decision required

How should the system stop offering a human-only card to unattended
workers? Options (not mutually exclusive):

- **A — Detect at `goc new`.** When a card is filed with a DoD item whose
  method class implies human-only execution (a heuristic over
  `EMPIRICAL:` items mentioning live/production/device actions), warn and
  suggest `--gate session`. Cheapest prevention, but heuristic and easy
  to phrase around; a warning, not a guarantee.
- **B — `goc validate` lint.** A warning-class finding
  (`HUMAN_ONLY_DOD_UNGATED` or similar) for an open `human_gate: none`
  card carrying a human-only `EMPIRICAL:` item. Runs in CI and on every
  refine pass, so it catches cards filed before the rule existed. Still
  advisory; relies on the tag being present and honest.
- **C — Core release-count auto-escalation.** Promote the downstream
  drain's release-attempt counter into `goc` itself: track auto-releases
  per card, and after a configurable budget escalate `human_gate` to
  `session` with a logged reason. Guarantees the loop self-terminates for
  *every* consumer, not just those who hand-rolled a net — but it is a
  reactive net, so it still spends the budget-many passes first. Best
  paired with A or B.
- **D — Do nothing in core; document the convention.** Rely on card
  authors to set `human_gate: session` on verify-first cards, and on each
  drain to build its own net (status quo). Rejected framing, listed for
  completeness: it is exactly the status quo that produced the wasted
  passes and pushed the fix into a downstream wrapper.

Recommendation leans **B + C**: the validate lint prevents most cases at
authoring/refine time across all consumers, and the core auto-escalation
is the backstop for the ones that slip through (or were filed before the
lint). A human should choose before implementation, since C relocates a
behaviour currently owned by downstream wrappers into the engine's gate
lifecycle.

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
summary: "Cards whose Definition of Done cannot be satisfied by an autonomous worker are still born at `human_gate: none`, because nothing inspects the DoD, so the picker offers them repeatedly and every pass is spent on a foregone conclusion. The escalation net that bounds this today lives in one downstream drain wrapper, so every other `goc` consumer has none. BLOCKED: the prerequisite `human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property` argues human-only-ness is per-DoD-item, not per-card, and must be decided first."
definition_of_done: |
  - [ ] PROCESS: the prerequisite `human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property` is decided FIRST — it disputes this card's premise and constrains every option here.
  - [ ] PROCESS: pick a mechanism from "## Decision required" (or a fifth) and record the choice + rationale here and in log.md. Any card-level mechanism must be justified against the prerequisite's "key off which items are human-only, not whether any item is" constraint, or this card closes as superseded (option E).
  - [ ] MECHANICAL: implement the chosen mechanism so that a card whose DoD cannot be satisfied by an autonomous worker no longer reaches one at `human_gate: none` unbounded — without freezing the agent-workable items of a mixed card. Touch `goc/engine.py` as the mechanism requires.
  - [ ] TDD: a regression test encodes the chosen behaviour AND covers the mixed card (agent-workable items plus one human-only item), asserting the mechanism does not park work an agent could still do. The test must NOT regress cards with genuinely autonomous DoD.
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

## Blocked on a prerequisite that disputes this card's premise

> ⚠ **Decide
> [`human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property`](../human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property/)
> first.** It carries `advances:` this card, and its own DoD requires
> reconciling with this one, "whose premise this card corrects."

That card's objection, in short: this card treats "human-only" as a
property of a *card*, but it is a property of each *DoD item*. The
downstream example cited above as the canonical structurally-human-only
card has **eight DoD items, exactly one of which is human-only**.
Detecting and gating it earlier — what options A/B below propose —
would have frozen the other seven sooner, which is a worse failure than
the one this card describes.

Its sharpest constraint on any mechanism shipped here:

> *"A lint that reads 'any `EMPIRICAL:` item mentioning a device or
> production ⇒ gate the card' would misfire on every mixed card in a
> deck. Whichever mechanism ships must key off which items are
> human-only, not whether any item is."*

So the options below are **not yet decidable as written** — A and B are
both card-level, and C's counter cannot tell a productive pass (boxes
ticked, no close) from a stalled one. Whether this card retains any
scope at all depends on which model that card picks: its option B
(per-item gating) would derive the effective gate from the DoD
automatically and could make A and B here unnecessary.

## Findings that survive regardless of the model chosen

Established while working this card on 2026-07-26; they constrain the
options but do not resolve them.

**Option A cannot hook `goc new`.** `goc new` stamps `draft: true` and
writes a *placeholder* DoD (`SCAFFOLD_DOD_PLACEHOLDER`); the real DoD is
authored afterwards into `README.md`. See `card_is_draft`
(`goc/engine.py:2450`). A heuristic there would inspect the placeholder
and find nothing. Any authoring-time detection must hook `_cmd_publish`
(`goc/engine.py:5631`) — where the authored DoD first reaches the queue,
and where the sibling `is_placeholder_scaffold` guard already lives.
This is a pure fact about the code and holds under every model.

**Counting `## ` headings in `log.md` is not a usable attempt metric.**
There is partial precedent for the engine reading log.md as machine
state (the `log-md-closure-entry` derived check, `goc/engine.py:5010`),
but that is a *presence check for one well-known heading at one decision
point*, not a tally over an open vocabulary. Heading formats are already
heterogeneous — `goc decide` writes `## {ts}: decision recorded`,
`goc done` writes `## {ts} — Closure`, `goc move` writes `## {ts}:
renamed from …`, and humans write free-form entries. A count would
measure how much has been *written about* a card rather than how often
work on it *failed*, and would make prose load-bearing for a scheduler
predicate.

**If C keeps a counter, it must reset on progress.** The prerequisite
card's own option C states the requirement directly: distinguish a pass
that ticked a box or landed a commit from a no-op pass. A counter that
increments on "released without closing" punishes productive partial
work on exactly the mixed cards that are most common.

## Decision required

How should the system stop offering a human-only card to unattended
workers? Options (not mutually exclusive) — **read the prerequisite
section above first; A and B as stated are card-level and the
prerequisite argues that shape misfires.**

- **A — Detect at publish time.** When a card is *published* with a DoD
  item whose method class implies human-only execution (a heuristic over
  `EMPIRICAL:` items mentioning live/production/device actions), warn and
  suggest raising the gate. Cheapest prevention, and it fires while the
  author still holds the context to act. But heuristic, easy to phrase
  around, and card-level as written. (Originally proposed at `goc new`;
  see the findings section for why that hook point is unimplementable.)
- **B — `goc validate` lint.** A warning-class finding
  (`HUMAN_ONLY_DOD_UNGATED` or similar) for an open `human_gate: none`
  card carrying a human-only `EMPIRICAL:` item. Runs in CI and on every
  refine pass, so it catches cards filed before the rule existed. Shares
  one predicate with A at a second call site. Still advisory; still
  card-level as written — would need to key off *which* items are
  human-only to satisfy the prerequisite.
- **C — Core release-count auto-escalation.** Promote the downstream
  drain's release-attempt counter into `goc` itself and escalate
  `human_gate` after a budget. Guarantees the loop self-terminates for
  *every* consumer, not just those who hand-rolled a net. Must reset on
  progress (see findings) or it punishes productive passes. A
  counter-free variant — a two-rung `waiting_on` → `human_gate` ladder
  reusing the self-clearing `waiting_until` overlay — is drafted in
  [`escalate-repeatedly-auto-released-cards-without-an-attempt-counter`](../escalate-repeatedly-auto-released-cards-without-an-attempt-counter/)
  (currently held as a draft pending this decision).
- **D — Do nothing in core; document the convention.** Rely on card
  authors to set the gate on verify-first cards, and on each drain to
  build its own net (status quo). Rejected framing, listed for
  completeness: it is exactly the status quo that produced the wasted
  passes and pushed the fix into a downstream wrapper.
- **E — Fold into the prerequisite; close this card as superseded.**
  If the prerequisite adopts per-item gating (its option B), the
  effective card gate is derived from the DoD automatically and this
  card's detection problem disappears. Worth considering rather than
  implementing a card-level mechanism the deck already documents as
  wrong.

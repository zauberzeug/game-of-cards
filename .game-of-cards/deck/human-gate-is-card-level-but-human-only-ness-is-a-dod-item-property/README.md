---
title: human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property
status: open
stage: null
contribution: medium
created: "2026-07-26T05:52:34Z"
closed_at: null
human_gate: decision
advances:
  - autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish
advanced_by: []
tags: [bug, api-contract]
summary: "`human_gate` is one flag per card, but human-only-ness is a property of individual DoD items. A card whose DoD is mostly agent-workable with one human-only box has no correct value: `none` gets it pulled, worked, and then auto-escalated to `session` by a release counter that cannot tell progress from stalling; `session` freezes the agent-workable majority. Worse, escalation is a one-way hand edit — `goc decide` lowers a gate, nothing raises one, and nothing records WHY it was raised, so an expired reason keeps a card parked indefinitely. Observed downstream: zoe-app's attachments card was gated for discovery boxes on 2026-07-20, those boxes were ticked on 2026-07-23, and it stayed parked (plus `status: active` on a dead worktree claim) until a human noticed on 2026-07-26."
definition_of_done: |
  - [ ] PROCESS: pick a model from "## Decision required" and record the choice + rationale here and in log.md; reconcile it with the sibling card `autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`, whose premise this card corrects.
  - [ ] MECHANICAL: a gate raised by tooling carries a machine-readable reason and, where the reason is a specific DoD item, a pointer to it — so a later pass can tell an expired gate from a live one instead of leaving it forever.
  - [ ] MECHANICAL: a verb raises the gate the way `goc decide` lowers it, writing the reason to frontmatter + log.md in one step; downstream wrappers stop hand-editing frontmatter with `sed`.
  - [ ] TDD: a regression test covers the mixed card — a DoD with agent-workable items AND a human-only item stays pullable while agent work remains, and stops being pullable when only the human-only item is left. It must not regress fully-autonomous or fully-human cards.
  - [ ] MECHANICAL: escalation no longer leaves a second, independent lock behind — a card taken out of an unattended worker's hands returns to `open` unless a human is actually holding it (see "## The second lock").
  - [ ] MECHANICAL: docs updated — card-schema (the `human_gate` lifecycle and its relationship to DoD method tags), create-card, pull-card, next-card, AGENTS; plugin mirrors synced; `uv run goc validate` clean.
---

# human_gate is card-level, but human-only-ness is a DoD-item property

## What's broken

`human_gate` is a single value per card. Whether a piece of work needs a
human is a property of each **DoD item**. Most cards are homogeneous, so
the flattening is invisible. Mixed cards — the common shape for
verify-first feature work — have no correct value:

- **`human_gate: none`** — the picker offers it, an agent does real work,
  and the pass ends without a close because the last box needs a human.
  Downstream wrappers then trip a release-attempt counter and escalate to
  `session`. The counter cannot distinguish *made progress but isn't
  finished* from *stalled*, so productive passes are punished exactly like
  wasted ones.
- **`human_gate: session`** — the human-only box is honoured, and the
  agent-workable majority of the card freezes with it. Nothing gets built
  until a human sits down for the whole card, which is the opposite of
  what the gate is for.

Neither value expresses the actual state: *an agent may work this card,
and may not close it.*

## The observed instance

zoe-app's `conversations-send-and-receive-file-attachments` (Slack-style
file attachments in a chat client):

| Date | Event |
|---|---|
| 2026-07-20 | Three DoD items need live-gateway discovery. An unattended drain burns two passes, its counter trips, gate raised `none → session`. **Correct at the time** — those three boxes really were human-only. |
| 2026-07-23 | An attended session does the discovery and ticks all three. The remaining boxes are two TDD, one sim-fixture, one docs — all agent-workable — plus one live/device check. |
| 2026-07-26 | Card still `human_gate: session`. Three days of queue time lost; a human had to notice by hand. |

The gate outlived its reason because **nothing recorded the reason**. The
escalation wrote prose into `log.md`, which no predicate reads. Ticking
the boxes that justified the gate did not, and could not, re-evaluate it.

## The second lock

The same escalation left `status: active` deliberately ("status
unchanged"), so the card was *also* invisible to the open queue, held by
a `worker:` pointing at a drain worktree deleted six days earlier.
Lowering the gate alone did not make the card pullable; it took a
separate `goc status … open`. One conceptual event — "an unattended
worker gave this card back" — is spread across two fields that must be
un-set independently, and the board renders the result as work in
progress.

Related but distinct:
[`active-state-conflates-being-worked-on-with-parked-at-human-gate`](../active-state-conflates-being-worked-on-with-parked-at-human-gate/)
argues the same conflation from the display side.

## Why the sibling card's premise is wrong

[`autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`](../autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/)
cites this exact zoe-app card as its canonical example of a
**structurally human-only** card, and proposes detecting such cards at
`goc new` / `goc validate` and gating them at `session` *earlier*.

That diagnosis does not survive contact with the card. Of eight DoD
items, exactly one is human-only. Escalating earlier would have frozen
the whole card sooner — the failure this card describes, harder. The two
cards share a symptom (wasted unattended passes) and need opposite
mechanisms:

- fully human-only card → keep it away from the picker (sibling card);
- **mixed** card → keep it *in* the picker, but stop the picker from
  treating "didn't close" as failure (this card).

A lint that reads "any `EMPIRICAL:` item mentioning a device or
production ⇒ gate the card" would misfire on every mixed card in a deck.
Whichever mechanism ships must key off *which* items are human-only, not
*whether any* item is.

## Decision required

- **A — Gate closure, not the pull.** A third `human_gate` value (say
  `closure`) meaning "agents may claim and advance; only a human may
  `goc done`". `goc done` already refuses on a non-`none` gate, so the
  enforcement point exists; the ready predicate would treat `closure`
  like `none`. Cheapest to implement, one new enum value, and it says
  exactly what is true. Cost: a third state everyone must learn, and it
  still does not say *which* box needs the human.
- **B — Per-item gating.** Mark the human-only DoD items themselves
  (a `HUMAN:` method tag, or a marker within the existing tags) and
  derive the effective card gate: pullable while an unmarked box is
  unticked, gated when only marked boxes remain. Most precise, needs no
  new card-level state, and it *self-clears* — ticking the last agent
  box raises the gate without anyone remembering to. Cost: DoD text
  becomes semantically load-bearing for a scheduler predicate, and the
  derivation must survive sloppy authoring.
- **C — Fix only the counter.** Leave the model alone; make release
  counters distinguish progress (a ticked box, a commit) from a no-op
  pass, and reset on progress. Smallest change, keeps the flattening.
  Cost: treats the symptom — a mixed card still ends up wrongly at
  `session` the moment progress genuinely stalls for two passes.
- **D — Split the card.** Convention only: authors keep each card
  gate-homogeneous and file the human-only verification as its own
  card. No engine change; costs a card per feature and relies on
  discipline the deck has already been observed not to keep.

Recommendation leans **B**, with **C** as an independent
robustness fix regardless of which model wins. B is the only option
that makes the gate track the DoD automatically, which is the actual
failure here: not that the gate was wrong, but that nothing re-evaluated
it when its justification expired.

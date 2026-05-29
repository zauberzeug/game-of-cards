---
title: parked-active-cards-are-missing-from-goc-ready-leverage-line
summary: "`render_leverage_line` (`goc/engine.py:2434`) is the function that produces the `Pulling X (value N). Highest gated card: Y (value M, gate …).` advisory that `goc --ready` appends after the queue table. It selects the comparison pool with `t.status == \"open\" and t.human_gate in (\"decision\", \"session\")`, silently excluding cards that were claimed (`status: active`) and *then* raised their gate. The Andon-cord signal documented in `Skill(pull-card)` — *\"when M >> N (≥3× higher value), ping the human to lower the gate\"* — therefore misreports M when the deck's highest-value gated card happens to be parked-active rather than parked-open. Third member of the same `status==\"open\" ∧ human_gate ≠ \"none\"` filter family as the closed [session-start-hook-shows-gated-active-cards-as-resumable](../session-start-hook-shows-gated-active-cards-as-resumable/) and the open [parked-active-cards-are-missing-from-goc-triage](../parked-active-cards-are-missing-from-goc-triage/)."
status: open
stage: null
contribution: medium
created: "2026-05-29T18:40:13Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - parked-active-cards-are-missing-from-goc-triage
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: fix-shape inherited from the resolution recorded on [parked-active-cards-are-missing-from-goc-triage](../parked-active-cards-are-missing-from-goc-triage/) (drop the `status` clause / split into two buckets / relabel). Record the inherited choice via `Skill(decide-card)` so the gate lowers to `none`.
  - [ ] TDD: a regression test exercises `render_leverage_line` against a fixture deck containing (a) a low-value ready card, (b) a medium-value open+gated card, (c) a high-value `status: active` + `human_gate: session` card. The test asserts the rendered "Highest gated card" entry names card (c), not card (b).
  - [ ] MECHANICAL: `render_leverage_line` (`goc/engine.py:2452-2457`) implements the chosen filter so parked-active cards participate in the gated-pool ranking on the same terms as parked-open cards.
  - [ ] EMPIRICAL: rerunning `goc --ready` on this repo's deck on a day where it carries parked-active cards (today, 2026-05-29, has two: value 15.3 and 9.0) surfaces one of those as `Highest gated card` if it outranks the highest open+gated card.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# `goc --ready` leverage line omits parked-active cards from the gated-comparison pool

## Location

`goc/engine.py:2434-2468` (`render_leverage_line`). The selection
filter is on lines 2452-2457:

```python
open_gated = [
    t for t in all_cards
    if t.status == "open"
    and t.human_gate in ("decision", "session")
    and not waiting_impedes(t)
]
```

`compute_values` and `sort_default` then rank `open_gated`; the top
entry is reported as the "Highest gated card" to compare against the
pulled card's value.

## What's broken

`Skill(pull-card)` documents the leverage line as the autonomous
puller's Andon-cord signal:

> The last line of `goc --ready` is a **leverage comparison**:
> `Pulling <title> (value N). Highest gated card: <title> (value M, gate <kind>).`
> When `M >> N` (≥3× higher value), the autonomous puller is about to
> work a small card while a much higher-value card sits parked behind
> a human gate — that's a signal to ping the human to lower the gate
> (`decide-card` for `decision`, the human's session for `session`)
> *before* draining low-value queue items.

The filter at `engine.py:2452-2457` makes the signal under-report.
A card enters the parked-active state through the normal lifecycle:
`pull-card` claims it (`goc status <title> active`), the agent reads
the body, finds work it can't finish without a human pick, raises the
gate to `decision` or `session` per the Andon-cord pattern, and
leaves. The card stays `status: active` with a raised gate. Every
other "active + gated" surface has been or is being reconciled with
this lifecycle — the SessionStart hook was just fixed (closed
2026-05-29 in `session-start-hook-shows-gated-active-cards-as-resumable`),
`_cmd_triage` has the open card
[`parked-active-cards-are-missing-from-goc-triage`](../parked-active-cards-are-missing-from-goc-triage/) —
but the leverage line still applies the legacy `status == "open"`
filter.

The harm is not theoretical: this very repo's deck on 2026-05-29
carries two parked-active gated cards
(`support-external-game-of-cards-state-location`, value 15.3, gate
`session`; `list-game-of-cards-on-anthropic-community-marketplace`,
value 9.0, gate `decision`) that are the **two highest-value gated
cards in the deck** but are invisible to `render_leverage_line`.

## Empirical evidence

A three-card fixture deck (created at `/tmp/test_leverage/.game-of-cards/deck/`
for this reproduction):

| title              | status | contribution | gate     | computed value |
|--------------------|--------|--------------|----------|----------------|
| `small-ready`      | open   | low          | none     | 1.0            |
| `big-open-gated`   | open   | medium       | decision | 3.0            |
| `huge-active-gated`| active | high         | session  | ~9.0           |

Running `goc --ready` on this fixture:

```
$ uv run python -m goc.cli --ready
ACTIVE: 1 claimed card outside this open queue: huge-active-gated. Check `goc --status active` or `goc --board` before claiming new work.
TITLE        STATUS  CONTR.  VALUE  GATE  TAGS  DOD
-----------  ------  ------  -----  ----  ----  ---
small-ready  open    low       1.0  none        0/1
Pulling small-ready (value 1.0). Highest gated card: big-open-gated (value 3.0, gate decision).
```

The leverage line names `big-open-gated` (value 3.0) as the highest
gated card; the actual highest gated card is `huge-active-gated`
(value ~9.0, ~9× the pulled value). The autonomous puller is told the
gap is 3× when it is actually 9×. The Andon-cord threshold (3× value
ratio) is silently shifted upward — the kind of high-leverage parked
work the line is explicitly designed to surface is precisely the kind
the filter hides.

The `ACTIVE:` line two rows above already names `huge-active-gated`,
which makes the inconsistency immediately visible to a reader: the
queue header acknowledges the card exists and is claimed, but the
leverage line refuses to rank it against the pulled card.

## Why it matters

The autonomous loop (`/loop pull-card`) is the consumer here. Every
loop iteration calls `goc --ready` and uses the leverage line to
decide whether to drain a small card or escalate to the human. When
the highest-value gated card in the deck is parked-active, the
escalation signal never fires — the loop keeps grinding through
small ready cards while a much larger amount of value sits parked.
This is exactly the failure mode the Andon cord is meant to prevent.

Reachability path: any session in which an agent claimed a card and
raised its gate mid-work produces the offending state. The two
in-flight parked-active cards on `main` today match this shape and
were both produced by exactly that lifecycle (per the closure note
on `session-start-hook-shows-gated-active-cards-as-resumable`).

## Fix

Whatever filter shape the
[`parked-active-cards-are-missing-from-goc-triage`](../parked-active-cards-are-missing-from-goc-triage/)
decision resolves to should be mirrored here. The two most likely
candidates from that card's `## Decision required` section translate
directly:

1. **Drop the `status` clause; gate the pool on `human_gate` and
   `not waiting_impedes` only.** Active+gated cards participate in
   the ranking on the same terms as open+gated cards. The leverage
   line reports the deck's actual highest-value gated card. Pros:
   sibling-consistent across all "active+gated" surfaces; the line
   regains its Andon-cord guarantee. Cons: an active+gated card
   "claimed" by the human's collaborator already implies someone
   knows about it — the ping may be redundant. (Counter-argument:
   the leverage line is for the autonomous puller, not the human;
   the loop benefits from seeing the total parked value regardless
   of who claimed it.)

2. **Two-bucket framing.** Compute the top open+gated AND the top
   active+gated separately, and render whichever is higher (or
   both, when their values differ significantly). Adds output
   complexity for a marginal precision gain.

Option 1 is the family-default fix shape (matches the closed
session-start hook resolution and the leading option on the open
triage card). The DoD pre-records that linkage; the actual decision
is recorded by `Skill(decide-card)` once the parent triage card
resolves.

For Option 1, the minimal patch at `engine.py:2452-2457`:

```python
open_gated = [
    t for t in all_cards
    if t.status in ("open", "active")
    and t.human_gate in ("decision", "session")
    and not waiting_impedes(t)
]
```

(The variable name `open_gated` then misnames the set — rename to
`parked_gated` or `gated_pool` in the same patch.)

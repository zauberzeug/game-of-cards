---
title: ready-leverage-line-goes-silent-when-no-card-is-pullable
summary: "`render_leverage_line` (`goc/engine.py`) returns \"\" whenever the ready set is empty, so the Andon-cord leverage advisory that `Skill(pull-card)` relies on to ping the human is suppressed in exactly the state where every remaining card needs a human to lower a gate. Live on this repo today: 0 pullable cards, 171 open cards parked behind a gate, top gated value 9.0 — and `goc --ready` prints no leverage line at all. Add one pullable card of value 3.0 and the same deck immediately emits a 3x-gap warning, so the signal is present at one ready card and absent at zero."
status: open
stage: null
contribution: high
created: "2026-07-31T06:19:39Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: the `## Decision required` question below is answered and recorded via `Skill(decide-card)`, lowering the gate to `none`.
  - [ ] TDD: `reproduce.py` exits zero — a deck whose only remaining open cards are gate-parked still emits an advisory naming the highest gated card.
  - [ ] TDD: a regression test pins the drained-queue advisory against a fixture deck (two gate-parked cards, zero pullable) and asserts the highest gated card is named. The existing one-pullable-card behaviour is asserted unchanged in the same test so the two shapes cannot drift.
  - [ ] MECHANICAL: `render_leverage_line` (`goc/engine.py:3425`) implements the chosen shape; `Skill(pull-card)`'s "the line is omitted when no gated cards exist or the queue is empty" sentence and its "Queue empty" stop-branch are updated to match, and the change is mirrored to the `.claude`/`claude-plugin`/`codex-plugin`/`openclaw-plugin` skill copies by the normal sync + porter run.
  - [ ] EMPIRICAL: `uv run goc --ready` on this repo's deck (0 pullable / 171 parked as of 2026-07-31) prints the advisory naming `ship-game-of-cards-as-cross-agent-cli` or whichever card then tops the gated pool; the output is recorded in `log.md`.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# The pull queue stops asking for help exactly when nothing is pullable

## Location

`goc/engine.py:3411-3448` (`render_leverage_line`). The suppression is
the function's first statement, `goc/engine.py:3425-3426`:

```python
    if not ready:
        return ""
    if values is None:
        values = compute_values(all_cards)
    open_gated = [
        t for t in all_cards
        if t.status == "open"
        and not card_is_draft(t)
        and t.human_gate in ("decision", "session")
        and not waiting_impedes(t)
    ]
```

The early return fires before `open_gated` is ever computed, so the
size and value of the parked pool cannot influence the outcome. The
one caller is `_cmd_default` at `goc/engine.py:3934-3937`, which
appends the result only under `--ready`.

## What's broken

`Skill(pull-card)` describes this line as the autonomous puller's
Andon cord — the mechanism by which a machine worker tells a human
the line needs them:

> When `M >> N` (≥3× higher value), the autonomous puller is about to
> work a small card while a much higher-value card sits parked behind
> a human gate — that's a signal to ping the human to lower the gate
> (`decide-card` for `decision`, the human's session for `session`)
> *before* draining low-value queue items.

The suppression rule is documented one sentence later — "The line is
omitted when no gated cards exist or the queue is empty" — so code
and doc agree. The defect is in what they agree on: the ping is
tied to the existence of a *pick to announce* rather than to the
existence of *parked work*.

That inverts the signal against its own rationale. One pullable
low-value card and the human is warned about the parked epic above
it; zero pullable cards — the strictly worse state, where the parked
work is not merely out-ranked but is the *only* work left — and the
warning is withheld. The parked cards are identical in both cases.

`Skill(scan-deck)` states the principle the behaviour violates:

> This is exactly the failure mode Lean's Andon was invented to
> prevent: a stopped line with no visible signal.

A fully-gated deck is a stopped line. `goc --ready` is the surface
the autonomous worker reads, and on a stopped line it prints nothing.

The consequence is not just a missing message. `Skill(pull-card)`'s
stop-branch for this state routes to discovery, not escalation:

> **Queue empty.** No ready cards. Invoke `Skill(audit-deck)` to file
> one new card from emergent codebase observations.

So the loop's entire response to "every card needs a human" is to
file another card — which, at the CLI's `decision` default gate,
lands parked too. The queue grows and the pullable count stays zero.
This very card was filed by that branch.

## Empirical evidence

`uv run python .game-of-cards/deck/ready-leverage-line-goes-silent-when-no-card-is-pullable/reproduce.py`:

```
=== synthetic deck ===
  epic-nobody-can-start-until-a-human-picks     status=open   gate=session  value=9.0 pullable=False
  second-card-waiting-on-a-decision             status=open   gate=decision value=3.0 pullable=False
  tiny-mechanical-cleanup                       status=open   gate=none     value=1.0 pullable=True

one card pullable  -> leverage line:
  Pulling tiny-mechanical-cleanup (value 1.0). Highest gated card: epic-nobody-can-start-until-a-human-picks (value 9.0, gate session).
zero cards pullable -> leverage line:
  (none)

=== this repo's live deck ===
  cards in deck            : 693
  pullable (goc --ready)   : 0
  open cards behind a gate : 171
  highest gated card       : ship-game-of-cards-as-cross-agent-cli (value 9.0, gate session)
  leverage line            : (none)

[FAIL] The advisory names the parked high-value card while one low-value
       card is still pullable, and disappears entirely once the queue
       drains — the parked cards are unchanged. The signal is present at
       one ready card and absent at zero.
```

Exit status 1. The live half needs no fixture: on 2026-07-31 this
repo's deck holds 174 open cards, of which 155 sit at `decision`, 16
at `session`, and the remaining 3 (`human_gate: none`) all carry an
active `waiting_on` overlay — so `goc --ready` returns zero rows and
prints only the active-card banner.

## Why it matters

The deck's autonomous half is designed to run unattended and to
interrupt a human only when it must. That contract only holds if the
interrupt actually fires. Today the interrupt is strongest when it is
least needed (one small card still pullable) and absent when it is
most needed (nothing pullable). A human reading `goc --ready` on a
fully-parked deck sees an empty queue and no indication that 171
cards are waiting on them specifically.

`goc triage` does list the parked cards, but it is a separate command
a human has to think to run; the leverage line is the push signal, and
it is the one the autonomous worker emits into its own transcript.

Related, and distinct:

- [parked-active-cards-are-missing-from-goc-ready-leverage-line](../parked-active-cards-are-missing-from-goc-ready-leverage-line/)
  and
  [ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card](../ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card/)
  are defects in *which cards enter* the `open_gated` comparison pool.
  This card is about the early return that runs before that pool is
  built, so neither fix reaches it.
- [pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty](../pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty/)
  covers the same drained-queue state on the CI side — the workflow's
  count predicate disagreeing with `goc --ready`. Fixing that one makes
  the workflow *stop* launching sessions on an empty queue, which
  removes the last surface that would have noticed the stall. The two
  should be resolved with each other in view.

## Decision required

The mechanical change is one branch; the question is what a drained
queue should emit, and on which surface.

**A — widen the existing line.** Keep one advisory, drop the `if not
ready` return, and render a no-pick variant: `Nothing pullable (0
ready). Highest gated card: <title> (value M, gate <kind>).` Smallest
diff, keeps one code path and one format for consumers that scrape
the line. Costs: `--ready` now prints on an empty queue, so any
caller treating "no output" as "no work" sees a behaviour change.

**B — emit a distinct stalled-deck banner.** Leave
`render_leverage_line` alone and add a separate renderer for the
zero-ready case that reports the parked *count* by gate plus the top
card, e.g. `Queue drained: 0 pullable, 171 parked (155 decision, 16
session). Highest: <title> (value 9.0). Run \`goc triage\`.` More
informative for the actual state, and does not overload a line whose
name and format say "leverage comparison". Costs: a second renderer
and a second format to keep in step with the first.

**C — treat it as a `Skill(pull-card)` change only.** Leave the engine
as is and rewrite the "Queue empty" stop-branch to run `goc triage`
and report the parked head *before* falling through to
`Skill(audit-deck)`. No engine change, no format churn, and it fixes
the loop behaviour that actually matters. Costs: the signal then
depends on an agent following prose rather than on the CLI emitting
it, and a human running `goc --ready` by hand still sees nothing.

Also to settle, whichever shape wins: should the queue-empty branch of
`Skill(pull-card)` keep filing an `audit-deck` card when the deck is
fully parked, or should escalation replace discovery in that state?
Filing more `decision`-gated cards into a 171-card parked backlog is
the behaviour that produced this card.

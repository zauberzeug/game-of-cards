---
title: ready-leverage-line-compares-a-worker-scoped-pick-against-every-workers-gated-cards
summary: "UNVERIFIED. On a runner with GOC_WORKER set, the --ready leverage line takes its 'Pulling' half from the worker-scoped queue but its 'Highest gated card' half from every worker's parked cards (render_leverage_line is passed the whole deck), while the ACTIVE banner and goc triage in the same invocation are worker-scoped. A scoped runner is told to ping a human about a card it could never pull, and its own parked card is never named."
status: open
stage: null
contribution: medium
created: "2026-09-28T01:36:15Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py builds a deck with one ready and one gated card per worker, runs `GOC_WORKER=<a> goc --ready`, and asserts the leverage line's gated half names only worker `<a>`'s cards — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] TDD: a regression test pins that the leverage line's gated pool is scoped by the same filters as its "Pulling" half (at least `--worker` / `GOC_WORKER`, matching the ACTIVE banner and `goc triage`)
  - [ ] MECHANICAL: drop the `unverified` tag once reproduce.py lands
---

# The `--ready` leverage line compares a worker-scoped pick against every worker's gated cards

> **UNVERIFIED.** Surfaced by an audit hunter on the engine query/render
> seam on 2026-09-28. The filing agent re-read and confirmed the
> citations. No `reproduce.py` was written this round; the falsification
> recipe is below.

## Location

All in `goc/engine.py`:

- `:3750-3756` (`render_leverage_line`, defined at `:3732`) builds the
  gated pool from `all_cards`:
  `open_gated = [t for t in all_cards if t.status == "open" and not card_is_draft(t) and t.human_gate in ("decision", "session") and not waiting_impedes(t)]`.
- `:4480` `render_leverage_line(filtered, cards, values=full_values)`.
  `filtered` is the worker-scoped queue; `cards` is the whole deck.
- `:4470-4472`, the banner beside it is scoped on purpose: "Scope the
  active-card banner to --worker … a worker-scoped queue must see only
  that worker's claimed cards."
- `:6994-6998`: `goc triage` filters parked cards by worker too.
- `:4026`: `--worker` defaults to `os.environ.get("GOC_WORKER")`.
- `goc/templates/skills/pull-card/SKILL.md:44-50`, the documented use of
  the line: "When `M >> N` (≥3× higher value) … that's a signal to ping
  the human to lower the gate … *before* draining low-value queue items."

## Hypothesis

On a runner that sets `GOC_WORKER`, the two halves of
`Pulling <title> (value N). Highest gated card: <title> (value M, gate <kind>).`
come from different populations:

- the "Pulling" half from the worker's queue;
- the "Highest gated card" half from every worker's parked cards.

A scoped runner is therefore told to ping a human about another worker's
card, one it could never pull. Its own parked card is never named when
another worker's outranks it. The ACTIVE banner and `goc triage`, under
the same invocation, are both worker-scoped, so this line is the only one
out of step.

The hunter's scratch deck held `alice-ready` (low), `alice-parked`
(medium, decision) and `bob-parked` (high, decision).
`GOC_WORKER=alice goc --ready` printed
`Pulling alice-ready-card (value 1.0). Highest gated card: bob-parked-card (value 9.0, gate decision).`,
a 9× gap that trips the ping rule. `GOC_WORKER=alice goc triage` listed
only `alice-parked-card`. `--tag` and `--contribution` are ignored by the
gated half in the same way.

## Why deferred

The citations are confirmed. No `reproduce.py` is committed this round.
Whether the gated pool should honor every query filter or only
`--worker` is left to the implementing agent. The minimum is `--worker`,
to match the banner and triage.

Related: the three leverage-line cards already filed cover other gaps in
the line:
[ready-leverage-line-goes-silent-when-no-card-is-pullable](../ready-leverage-line-goes-silent-when-no-card-is-pullable/)
(the empty queue),
[parked-active-cards-are-missing-from-goc-ready-leverage-line](../parked-active-cards-are-missing-from-goc-ready-leverage-line/)
(parked-active cards), and the closed
[ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card](../ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card/)
(draft scaffolds). None covers worker scope.

## Falsification recipe

In a scratch deck, give worker `bob` a gated high-contribution card and
worker `alice` a ready low one. Run `GOC_WORKER=alice goc --ready`. If
the leverage line does not name `bob`'s card, the hypothesis is
disproved.

Surfaced by: general-purpose audit hunter (engine query / render
surface), 2026-09-28.

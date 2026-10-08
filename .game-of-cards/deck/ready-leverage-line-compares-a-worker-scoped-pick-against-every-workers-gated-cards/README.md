---
title: ready-leverage-line-compares-a-worker-scoped-pick-against-every-workers-gated-cards
summary: "On a runner with GOC_WORKER set, the --ready leverage line took its 'Pulling' half from the worker-scoped queue but its 'Highest gated card' half from every worker's parked cards, because render_leverage_line was passed the whole deck. The ACTIVE banner and goc triage in the same invocation are worker-scoped. A scoped runner was told to ping a human about a card it could never pull, and its own parked card was never named. Confirmed by reproduce.py. Fixed: the gated half now draws from the query's whole scope (--worker/GOC_WORKER, --tag, --contribution, --stage, --advances, --advanced-by), so it names the card this queue would pull if a human lowered its gate."
status: done
stage: null
contribution: medium
created: "2026-09-28T01:36:15Z"
closed_at: "2026-10-08T05:15:05Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py builds a deck with one ready and one gated card per worker, runs `GOC_WORKER=<a> goc --ready`, and asserts the leverage line's gated half names only worker `<a>`'s cards — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] TDD: a regression test pins that the leverage line's gated pool is scoped by the same filters as its "Pulling" half (at least `--worker` / `GOC_WORKER`, matching the ACTIVE banner and `goc triage`)
  - [x] MECHANICAL: drop the `unverified` tag once reproduce.py lands
worker: {who: "claude[bot]", where: main}
---

# The `--ready` leverage line compares a worker-scoped pick against every worker's gated cards

> **Confirmed and fixed.** An audit hunter surfaced this on the engine
> query/render seam on 2026-09-28. `reproduce.py` confirmed it, and the
> gated half of the line now shares the query's scope. Regression tests:
> `tests/test_leverage_line_query_scope.py`.

## Location

All in `goc/engine.py`:

- `render_leverage_line` builds the gated pool from the `cards` it is
  handed:
  `open_gated = [t for t in cards if t.status == "open" and not card_is_draft(t) and t.human_gate in ("decision", "session") and not waiting_impedes(t)]`.
- `_cmd_default` called it as `render_leverage_line(filtered, cards, values=full_values)`.
  `filtered` is the worker-scoped queue and `cards` is the whole deck.
- The ACTIVE banner beside it is scoped on purpose: "Scope the
  active-card banner to --worker … a worker-scoped queue must see only
  that worker's claimed cards."
- `_cmd_triage`: `goc triage` filters parked cards by worker too.
- `--worker` defaults to `os.environ.get("GOC_WORKER")`.
- `goc/templates/skills/pull-card/SKILL.md`, the documented use of the
  line: "When `M >> N` (≥3× higher value) … that's a signal to ping the
  human to lower the gate … *before* draining low-value queue items."

## Defect (confirmed)

On a runner that sets `GOC_WORKER`, the two halves of
`Pulling <title> (value N). Highest gated card: <title> (value M, gate <kind>).`
came from different populations:

- the "Pulling" half from the worker's queue;
- the "Highest gated card" half from every worker's parked cards.

A scoped runner was therefore told to ping a human about another
worker's card, one it could never pull. Its own parked card was never
named when another worker's card outranked it. The ACTIVE banner and
`goc triage` in the same invocation are both worker-scoped, so this line
was the only one out of step. `--tag`, `--contribution`, `--stage`,
`--advances` and `--advanced-by` were ignored by the gated half in the
same way.

`reproduce.py` builds a deck with one ready and one gated card per
worker. bob's gated card outranks alice's. Before the fix,
`GOC_WORKER=alice goc --ready` printed
`Pulling alice-ready (value 1.0). Highest gated card: bob-parked (value 9.0, gate decision).`.
That is a 9× gap, which trips the ping rule, and `reproduce.py` exits 1.
After the fix it prints `... Highest gated card: alice-parked (value 3.0, gate decision).`
and exits 0.

## Fix

The filing left one choice to the implementing agent: should the gated
pool honor only `--worker`, or every query filter? The fix takes every
scope filter. The leverage line exists to say that lowering a gate would
change what this puller works on next. That holds only for a gated card
the same query would pull once ungated. A card outside the `--tag` scope
is out of reach in the same way as one outside the `--worker` scope.

- `_cmd_default` keeps the query's scope filters (`stages`,
  `contribution`, `tags`, `advances`, `advanced_by`, `worker`) in one
  `scope` dict. The lifecycle conjuncts (`status`, `human_gate`, `since`,
  `ready`) stay separate. `run_query` applies both. The leverage line's
  gated pool is `filter_cards(cards, status=None, **scope)`, the scope
  alone. A scope filter added later reaches both halves without a second
  edit.
- `render_leverage_line` keeps the gated half's own lifecycle predicate
  (open, gated, not a draft, not impeded). Widening that predicate needs
  one edit, in one place. The decision-gated
  [parked-active-cards-are-missing-from-goc-ready-leverage-line](../parked-active-cards-are-missing-from-goc-ready-leverage-line/)
  would be such a widening.
- `render_leverage_line` now takes a `by_title` keyword, as
  `render_active_notice` does. `_cmd_default` threads the full-deck
  lookup, so the near-term-flow tiebreak still counts live downstream
  cards that the scope hides.
- The query's `--human-gate` filter deliberately stays out of the gated
  pool. The gate is the one conjunct the two halves differ on.
  `goc --ready --human-gate none` is redundant, and it must not silence
  the line.
- The pull-card skill now says the gated card comes from the same scope
  as the pick. It also says the line is omitted when no gated card
  exists *in that scope*.

The ACTIVE banner stays scoped by `--worker` only. It is a soft-lock
hint about claimed work, and conflicting work can cross a tag boundary.

Related: three other leverage-line cards cover other gaps in the line:
[ready-leverage-line-goes-silent-when-no-card-is-pullable](../ready-leverage-line-goes-silent-when-no-card-is-pullable/)
(the empty queue),
[parked-active-cards-are-missing-from-goc-ready-leverage-line](../parked-active-cards-are-missing-from-goc-ready-leverage-line/)
(parked-active cards), and the closed
[ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card](../ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card/)
(draft scaffolds). None of them covers query scope.

Surfaced by: general-purpose audit hunter (engine query / render
surface), 2026-09-28.

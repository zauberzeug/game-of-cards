---
title: reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate
summary: "The reproduce.py of deck-fills-with-decision-gated-cards-faster-than-they-are-decided measures its autonomous runway as runway = gates.get(\"none\", 0) — a bare human_gate count over open+active cards. The engine's card_is_ready also excludes impeded cards, unpublished drafts, and cards already claimed. On 2026-08-24 the script reported runway 5 while goc --ready returned no cards at all, so the card's DoD gate (runway at least 15) can go green with a real runway of zero. Seventh known hand-rolled copy of the pull-readiness predicate, and a fail-open defect test."
status: active
stage: null
contribution: medium
created: "2026-08-24T02:31:19Z"
closed_at: null
human_gate: none
advances:
  - extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate
advanced_by: []
tags: [bug, test, api-contract]
definition_of_done: |
  - [ ] TDD: a falsifying probe exits non-zero on today's script — construct a deck (or a stub card list) with 15+ `human_gate: none` cards that are all impeded, drafts, or `active`, and show the current `runway` metric reports 15+ while `card_is_ready` reports 0. It must exit zero after the fix.
  - [ ] MECHANICAL: `reproduce.py` in `deck-fills-with-decision-gated-cards-faster-than-they-are-decided` derives its runway from the engine — either by shelling out to `goc --ready --json` or by importing `card_is_ready` — rather than counting `human_gate`. It already shells out to `goc` for the card list, so no new dependency is introduced.
  - [ ] MECHANICAL: the gate count is kept as a *separate* reported line (it is the upper bound and the card's intake argument uses it), so the fix adds a number rather than replacing an argument.
  - [ ] MECHANICAL: the parent card's `## Empirical evidence` block and its `## What's broken` table are re-rendered from the fixed script, and DoD item 1 there ("the autonomous runway is at least 15 open cards") reads against the engine predicate.
  - [ ] EMPIRICAL: run the fixed script on this repo's deck and record both numbers in that card's `log.md`. Today they are 5 and 0.
  - [ ] PROCESS: decide and record whether the sibling deck scripts carry the same drift — a sweep of `.game-of-cards/deck/*/reproduce.py` for `human_gate` / `"none"` comparisons that stand in for pullability. Report the count even if it is zero; a silent sweep is the failure mode this card is an instance of.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
worker: {who: "claude[bot]", where: main}
---

# A card's runway metric counts gates where the engine counts pullability

## Location

- `.game-of-cards/deck/deck-fills-with-decision-gated-cards-faster-than-they-are-decided/reproduce.py:91`
  — `runway = gates.get("none", 0)`
- `goc/engine.py:2582` — `card_is_ready`, the predicate the picker actually uses
- `goc/engine.py:2695` — `live_impeded`, one of the axes the script omits

## What's broken

The script measures the autonomous runway with a one-axis count:

```python
gates = Counter(c["human_gate"] for c in live)
runway = gates.get("none", 0)
```

`live` is every card with `status in ("open", "active")`. The engine's
`card_is_ready` gates on four things, not one — status must be `open`
(so a claimed `active` card is out), the gate must be `none`, the card
must not be an unpublished draft, and it must carry no active impediment
overlay. Three of those four axes are missing from the script, so its
`runway` is an upper bound on the runway rather than the runway.

The gap is not theoretical, and it is widest exactly where the number
matters. Measured on this repo's deck, 2026-08-24:

```
$ uv run python .../reproduce.py
autonomous runway (gate=none, claimable by the picker): 5

$ uv run goc --ready
No cards match (ready: status open, gate none, no active impediment;
1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
```

All five of the `human_gate: none` cards are excluded by an axis the script
does not read:

| card | axis that excludes it |
|---|---|
| `openclaw-plugin-skills-force-repeated-reads-every-session` | `status: active` + `waiting_on: external` |
| `openclaw-subagent-plugin-tools-alsoallow-ignored` | `waiting_on: external` |
| `blocked-status-conflates-dependency-external-wait-and-deferral` | `waiting_on: deferred` |
| `remove-blocked-from-status-enum-and-migrate-existing-cards` | `waiting_on: deferred` |
| `escalate-repeatedly-auto-released-cards-without-an-attempt-counter` | `draft: true` |

So the script prints 5 for a deck on which the picker can claim nothing.

## Why it matters

Two independent reasons, and the second is the one that makes this worth a
card rather than a one-line edit.

**It is a fail-open defect test.** The parent card's DoD item 1 reads "TDD:
`reproduce.py` exits zero — the autonomous runway is at least 15 open cards."
Fifteen gate-free cards that are all impeded, claimed, or drafts would satisfy
that with a real runway of zero: the card would close as fixed while the
symptom it was filed about — the loop having no work — was total. The witness
cannot distinguish "the runway recovered" from "the gate count recovered",
which is the two-passing-states shape
[static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
describes for prohibition scanners, arriving here through a threshold instead
of an empty list.

**It understates the defect it is evidence for.** The parent card argues that
the deck fills with gated cards faster than they are decided, and its
headline number is the runway. Reporting 5 rather than 0 makes the situation
look like "a few days of loop left" when the correct reading is "the loop is
already starved". A dashboard that is wrong in the direction of reassurance is
worse than no dashboard.

## Family

This is the seventh known hand-rolled copy of the pull-readiness predicate,
and the first one inside the deck rather than in shipped code.
[extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate](../extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate/)
is the family root and enumerates copies one to five (`card_is_ready`,
`card_is_workable_for_scheduler`, the board's `not_ready` cell,
`.github/workflows/pull-card.yml`, and `render_empty_query_line`); the sixth
was the `standup` skill's "Next up" block, closed 2026-08-23 by
[standup-next-up-section-lists-cards-pull-card-would-never-pick](../standup-next-up-section-lists-cards-pull-card-would-never-pick/)
with the one-token substitution `goc` → `goc --ready`. That card measured
precision 0/3 against a true ready count of 0 — the same measurement, one day
earlier, on a different surface.

The root card's chosen fix shape ("expose the engine predicate, don't re-roll
it") applies unchanged, and the substitution here is the same size: the script
already shells out to `goc --status all --json`, so `goc --ready --json` costs
one more call and no new dependency. It is filed separately rather than folded
into the root because the root's DoD is about a Python introspection guard
over three in-engine copies, and a deck-local script is reachable by neither
that guard nor `goc validate`.

## Why it is filed rather than fixed here

The hygiene pass that found it was refreshing the parent card's stale
dashboard, and the parent is parked at `human_gate: decision`. Editing the
threshold test of a parked card changes what that card claims is true, which
belongs to whoever decides it — the fix flips DoD item 1 from a number that
can be satisfied by drift to one that cannot, and that is a change in the
card's contract, not a repair to its prose. The measurement itself is written
into the parent's README and `log.md` in place, so the number a reader sees
there is already correct.

## Non-goals

- Not a change to `card_is_ready` or to any engine predicate. The engine is
  right; the script disagrees with it.
- Not the fix for the parent card's actual defect (the gated backlog has no
  outlet). That is parked on a human decision and unaffected by this.
- Not a general audit of deck scripts. DoD item 6 asks for the sweep's
  *count* precisely so that scope stays bounded and reported rather than
  silently skipped.

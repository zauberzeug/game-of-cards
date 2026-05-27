---
title: board-marks-pullable-and-impeded-cards-with-the-same-hourglass-glyph
summary: "`goc --board` paints the same ⏳ glyph on two states with opposite pull semantics: a dependency-awaiting card (pullable — `card_is_ready` no longer treats an open `advanced_by` prereq as blocking) and a genuinely impeded card (`waiting_impedes` — queue-hidden). The primary human triage surface cannot distinguish 'you may start' from 'do not pull'. UNVERIFIED: the collision is visible in the code, but the claim that this contradicts a closed card's DoD needs confirmation, and the fix is a UX taste call."
status: open
stage: null
contribution: medium
created: "2026-05-27T09:35:28Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py builds a 3-card deck (open prereq; a dependent card `advanced_by` it; an impeded card with a future `waiting_until`) and asserts the board renders a *distinct* marker for the pullable dependency-awaiting card vs. the queue-hidden impeded card. Fails before the fix.
  - [ ] PROCESS: the `## Decision required` below is resolved — pick the marker scheme (distinct glyph, or only mark `waiting_impedes`).
  - [ ] PROCESS: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green; drop the `unverified` tag once reproduce.py lands.
---

# board uses one ⏳ glyph for pullable dependency-awaiting and queue-hidden impeded cards

> Filed UNVERIFIED by the audit-deck impediment/readiness hunter (general-purpose
> agent, 2026-05-27). The code collision is real and quoted below; the
> design-intent contradiction and the right fix are not yet confirmed.

## Location

`goc/engine.py:2212-2217` — the board cell renderer.

## Hypothesis (verbatim quote)

```python
live = t.status not in TERMINAL_STATUSES
not_ready = live and (
    (t.status == "open" and dependency_blocked(t, by_title)) or waiting_impedes(t)
)
if not_ready:
    marker += " ⏳"
```

`card_is_ready` (`goc/engine.py:1694`) deliberately **does not** treat
`dependency_blocked` as blocking — an open `advanced_by` prereq is advisory
("you may start"), only `waiting_impedes` and `human_gate` hide a card from the
pull queue. The `-v` queue line and the JSON `dependency_awaiting` key
(`goc/engine.py:2175`) reflect this neutral framing. But the board bundles
`dependency_blocked` and `waiting_impedes` into one `not_ready` variable and
paints the **same ⏳ glyph** for both. So on the board, a pullable
dependency-awaiting card is visually indistinguishable from a card that must not
be pulled.

The agent noted the closely-related closed card
[`board-omits-marker-for-cards-with-active-waiting-overlay`](../board-omits-marker-for-cards-with-active-waiting-overlay/)
*added* the impediment marker by reusing ⏳ rather than introducing a distinct
glyph — which is how the two states ended up collapsed.

## Why deferred (unverified)

Two things need confirming before this is a settled defect:

1. **Design-intent contradiction.** The agent asserts a closed card's DoD
   required *relabeling* the board so dependency-awaiting reads as "you may
   start". That claim must be checked against the actual body/DoD of
   `make-advances-gate-closure-not-the-pull-queue` (and the waiting-overlay
   card) — if no such requirement exists, this is a UX nicety, not a contract
   drift.
2. **No reproduce.py budget this round** — the primary audit finding
   (`yaml-lite-truncates-flow-collection-with-hash-in-quoted-element`) consumed
   the verification budget.

## Falsification recipe

Build a deck with three cards: `upstream-prereq` (status open), `dependent`
(`advanced_by: [upstream-prereq]`), `impeded` (`waiting_on: external,
waiting_until: 2099-01-01`). Assert `card_is_ready(dependent) is True` and
`card_is_ready(impeded) is False`, then render the board and check whether
`dependent` and `impeded` carry the *same* marker substring. If they do, the
defect is confirmed; if the board already distinguishes them, disprove this
card.

## Decision required

If confirmed, which marker scheme?

- **(a)** Distinct glyph per state — e.g. keep ⏳ for impeded (`waiting_impedes`),
  introduce a separate advisory marker (or none) for dependency-awaiting.
- **(b)** Only mark `waiting_impedes` on the board; drop the
  `dependency_blocked` arm entirely (dependency-awaiting is pullable, so it
  needs no "stop" signal).

(b) is simpler and matches the "advisory only" framing; (a) preserves an
at-a-glance "this has an open prereq" hint. Pick before implementing.

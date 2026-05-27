---
title: board-omits-marker-for-cards-with-active-waiting-overlay
summary: "The kanban board (`goc --board`) marks dependency-blocked open cards with a ⏳ glyph but gives no marker to a card carrying an active `waiting_on`/future-`waiting_until` impediment overlay. Such a card is hidden from the pull queue by `card_is_ready` yet renders identically to a genuinely pullable card on the board — the primary human triage surface — so a human reading the board cannot tell an impeded card from an available one."
status: done
stage: null
contribution: medium
created: "2026-05-27T07:38:40Z"
closed_at: 2026-05-27T07:45:05Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — an open card with an active impediment overlay renders on the board with a distinguishing marker (so it is no longer identical to a pullable card).
  - [x] MECHANICAL: `card_cell` in `render_board` (`goc/engine.py`) adds an impediment marker when `waiting_impedes(t)` is true, alongside (and visually distinct from, or shared with) the existing dependency-blocked ⏳.
  - [x] PROCESS: the marker semantics are documented wherever the board legend / dependency-block ⏳ is described (deck skill board section, if any), so a reader knows what the glyph means.
worker: {who: "claude[bot]", where: main}
---

# Board gives no marker to a card carrying an active impediment overlay

## Location

`goc/engine.py:2209-2217` — `card_cell` inside `render_board`.

## What's broken

The three-axis model (see
[blocked-status-conflates-dependency-external-wait-and-deferral](../blocked-status-conflates-dependency-external-wait-and-deferral/))
gives a card three independent "can't pull yet" signals: a non-terminal
`advanced_by` prereq (derived dependency-block, *advisory*), a raised
`human_gate`, and an **active impediment overlay** (`waiting_on` reason
or a future `waiting_until`). The overlay is the *hard* "must wait"
signal — `card_is_ready` excludes any impeded card from the pull queue:

```python
def card_is_ready(card: Card, by_title: dict[str, Card]) -> bool:
    if card.status != "open":
        return False
    if card.human_gate != "none":
        return False
    if waiting_impedes(card):
        return False
    return True
```

But the board renderer marks only the *advisory* dependency-block, never
the *hard* impediment overlay:

```python
def card_cell(t: Card) -> str:
    c = t.contribution or ""
    marker = f" [{c[0] if c else '?'}]"
    if t.status == "open" and dependency_blocked(t, by_title):
        marker += " ⏳"
    who = _worker_who(t.frontmatter.get("worker"))
    if who:
        marker += f" @{who[:8]}"
    return f"{t.title}{marker}"
```

So a card with `waiting_on: external` (or a future `waiting_until`)
appears in the OPEN column rendered byte-identically to a genuinely
pullable card — same `[h]` contribution marker, no ⏳, nothing.

This is a renderer/predicate divergence. The DoD of
[add-waiting-overlay-with-reason-and-until-date](../add-waiting-overlay-with-reason-and-until-date/)
delivered the read-time queue guard (`waiting_impedes` hides the card
from `next-card`/`pull-card`) but did **not** include a board marker;
the only board work that landed was
[derive-dependency-readiness-instead-of-storing-blocked-status](../derive-dependency-readiness-instead-of-storing-blocked-status/),
whose DoD covered the *derived dependency-block* marker only. The
impediment overlay fell through the gap between the two cards.

## Empirical evidence

`uv run python deck/board-omits-marker-for-cards-with-active-waiting-overlay/reproduce.py`:

```
=== card_is_ready (the pull-queue predicate) ===
  plain-pullable-card      ready=True
  impeded-card             ready=False

=== render_board OPEN column cells ===
  'plain-pullable-card [h]'
  'impeded-card [h]'

=== verdict ===
  plain_is_ready   = True
  impeded_is_ready = False
  plain_board_marker   = ' [h]'
  impeded_board_marker = ' [h]'

DEFECT CONFIRMED: impeded card is hidden from the pull queue (ready=False)
but the board renders it with no ⏳ overlay marker — indistinguishable
from the pullable card.
```

## Why it matters

`goc --board` is the primary human triage surface. A human curating the
queue (the Kanban steering job the whole pull model depends on) reads the
OPEN column to decide what is workable. An impeded card sitting there with
no marker invites the human to "just pull that one" — exactly the work the
overlay was added to fence off. Worse, the dependency-block ⏳ *is* shown,
so a reader reasonably infers "no glyph ⇒ ready", which is false for
impeded cards. The board silently under-reports the deck's true state.

## Fix (applied)

`card_cell` now emits a single shared "not-ready" glyph (⏳) when a card
is either dependency-blocked OR carries an active impediment overlay,
collapsing both signals into one condition so no card gets a doubled
glyph:

```python
not_ready = (t.status == "open" and dependency_blocked(t, by_title)) or waiting_impedes(t)
if not_ready:
    marker += " ⏳"
```

Dependency-block and impediment share one glyph: the board's only
contract is "⏳ ⇒ not pullable, no glyph ⇒ pullable", which is the
distinction a human curating the queue needs. The glyph is documented
in the deck skill's `goc --board` legend row.


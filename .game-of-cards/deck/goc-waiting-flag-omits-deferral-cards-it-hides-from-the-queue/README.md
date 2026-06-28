---
title: goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue
status: done
stage: null
contribution: medium
created: "2026-06-24T19:55:57Z"
closed_at: "2026-06-24T20:03:40Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "`goc --waiting` filters on `waiting_on is not None` instead of the canonical `waiting_impedes()` predicate that `card_is_ready`, the board ⏳ marker, and the leverage line all use. So a bare deferral set with `goc wait <t> --until <future>` (no `--reason`) is hidden from the queue and marked ⏳ on the board, yet is invisible to `--waiting` — while an elapsed wait that has re-entered the queue is still listed. Align the filter with `waiting_impedes`."
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the set `goc --waiting` returns equals the set of cards `waiting_impedes` considers impeded.
  - [x] MECHANICAL: the `--waiting` filter in `_cmd_list` calls `waiting_impedes(t)` instead of restating `t.waiting_on is not None`; the `--waiting` help text matches the impediment semantics.
  - [x] TDD: a regression test asserts `--waiting` includes a bare `--until`-only deferral (impeded) and excludes an elapsed `waiting_until` (resurfaced).
  - [x] PROCESS: `uv run python -m unittest discover -s tests` green; `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc --waiting` omits deferral cards it hides from the queue

## Location

`goc/engine.py`, the `--waiting` filter inside `_cmd_list`:

```python
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if t.waiting_on is not None]
```

## What's broken

The `--waiting` filter keeps a card iff `t.waiting_on is not None`. But the
canonical "is this card impeded right now?" predicate is `waiting_impedes(card)`
(`engine.py`), which every other consumer of the impediment overlay already
calls:

- `card_is_ready` (`engine.py:2213`) — hides impeded cards from the queue.
- `card_is_workable_for_scheduler` (`engine.py:2238`) — prunes impeded
  descendants from value composition.
- the board renderer (`engine.py:2975`) — paints the ⏳ marker.
- the leverage line (`engine.py:3053`).

`--waiting` is the lone outlier that re-states a *weaker* condition by hand,
and the two disagree in both directions:

- **Under-inclusion.** `goc wait <title> --until <future-date>` with no
  `--reason` is a supported CLI form (`_cmd_wait` only errors when *both*
  `--reason` and `--until` are absent; it even prints `(no reason set; implied
  'deferred')`). The resulting card has `waiting_on=None`,
  `waiting_until=<future>`, so `waiting_impedes` is `True` — it is hidden from
  `--ready` and painted ⏳ on the board — yet `--waiting`, the command whose
  entire job is to surface waiting cards, omits it.
- **Over-inclusion.** A card with `waiting_on` set and `waiting_until` in the
  *past* has `waiting_impedes == False`: by design it has RE-ENTERED the queue
  (the elapsed wait self-clears; `validate` surfaces it separately as an SLE
  escalation). `--waiting` still lists it because `waiting_on is not None`,
  contradicting the board (no ⏳) and `--ready` (card present).

The help text — `"Filter to cards carrying a waiting_on overlay."` — describes
the buggy `waiting_on`-only condition; it predates the bare-deferral and
elapsed-resurface refinements that gave `waiting_impedes` its current shape.

## Empirical evidence

`uv run python deck/goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue/reproduce.py` — post-fix:

```
goc --waiting returns : ['bare-deferral', 'open-block']
waiting_impedes True  : ['bare-deferral', 'open-block']
PASS: --waiting matches the waiting_impedes predicate
```

Before the fix the same script reported the divergence the bug describes —
`bare-deferral` (impeded, hidden from `--ready`, ⏳ on the board) was absent
from `--waiting`, while the resurfaced `elapsed-wait` was still listed:

```
goc --waiting returns : ['elapsed-wait', 'open-block']
waiting_impedes True  : ['bare-deferral', 'open-block']
UNDER-included (impeded but absent from --waiting): ['bare-deferral']
OVER-included  (in --waiting but not impeded)     : ['elapsed-wait']
FAIL: --waiting diverges from waiting_impedes
```

## Why it matters

`--waiting` is the human's review surface for "what is parked and why" — it is
how an operator finds a card that has silently dropped out of the queue. A
bare deferral (`goc wait <t> --until <date>`) is the one overlay shape that is
hidden from the queue *without* a `waiting_on` reason, so it is exactly the
case where "where did my card go?" most needs an answer — and it is the case
`--waiting` cannot answer today. The standup skill's JSON filter
(`[c for c in cards if c.get('waiting_on')]`) carries the same blind spot, but
it is downstream of this engine bug; this card fixes the engine filter, the
single source of truth the flag exposes.

## Fix

Replace the hand-rolled condition with the shared predicate so the set
`--waiting` shows is exactly the set hidden from `--ready` and marked ⏳:

```python
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if waiting_impedes(t)]
```

and update the `--waiting` help text to describe the impediment semantics
(an active overlay: a `waiting_on` reason or an unelapsed `waiting_until`).
No new decision: `waiting_impedes` already defines "impeded" and is used by
four sibling sites; this call site is simply brought into line.

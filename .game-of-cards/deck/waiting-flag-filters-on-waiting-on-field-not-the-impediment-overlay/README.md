---
title: waiting-flag-filters-on-waiting-on-field-not-the-impediment-overlay
summary: "`goc --waiting` filters with `t.waiting_on is not None`, so a card deferred via `goc wait --until <future>` with no `--reason` (a bare `waiting_until`, which `waiting_impedes` treats as an active `deferred` overlay and the board flags ⏳) is invisible in the one view meant to surface impeded work. The fix needs a small decision: filter on overlay-field-presence (matches the help text) or on the `waiting_impedes` predicate (matches --ready / the board)."
status: open
stage: null
contribution: medium
created: "2026-06-19T05:24:35Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded — `--waiting` filters on overlay-field-presence OR on `waiting_impedes` (see "## Decision required")
  - [ ] TDD: reproduce.py exits zero — a bare-`waiting_until` deferred card appears (or is consistently excluded, per the decision) in `goc --waiting`, matching the board/`--ready` treatment
  - [ ] TDD: regression test under tests/ pins the chosen semantics
  - [ ] `uv run python -m unittest discover -s tests` passes
  - [ ] `uv run goc validate` passes
---

# `goc --waiting` filters on the `waiting_on` field, not the impediment overlay

## Location

`goc/engine.py:3330-3331`.

## What's broken

```python
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if t.waiting_on is not None]
```

The `--waiting` flag is documented (engine.py:3013) as:

> Filter to cards carrying a waiting_on overlay.

But the three-axis stuck model defines the stored impediment overlay as
`waiting_on` set **or** a bare `waiting_until` — `waiting_impedes`
(engine.py:2136) and its docstring state that "A `waiting_until` in the
future implies a `deferred` wait" and hides the card from queues. A card
deferred with `goc wait <title> --until <future-date>` and **no** `--reason`
therefore:

- has `waiting_on is None` but `waiting_until` set,
- is hidden from `--ready` (because `waiting_impedes` returns True),
- is flagged `⏳` on the board,
- yet is **omitted** from `goc --waiting` — the one view whose purpose is to
  surface impeded/waiting work.

So a genuinely-impeded deferred card is invisible exactly where an operator
goes to find impeded cards. The `--waiting` filter has drifted from the
engine's own `waiting_impedes` predicate that `--ready` and the board use.

## Reachability path

`goc wait <title> --until 2099-01-01` (no `--reason`) writes a bare
`waiting_until` overlay; `goc --waiting` then drops the card. This is a real,
documented `goc wait` usage (the deferral form), not a hand-edited shape.

## Why this is a decision, not a clean fix-through

Two credible fixes exist and they differ in a second case:

1. **Overlay-field-presence** — `t.waiting_on is not None or t.waiting_until is not None`.
   Matches the help text literally ("carrying a waiting_on overlay", where a
   bare `waiting_until` *is* an overlay). A strict superset of today's
   behavior: it also keeps a card that has `waiting_on` set but an *elapsed*
   `waiting_until` (which has re-entered the queue).
2. **Impediment predicate** — `waiting_impedes(t)`. Matches `--ready` and the
   board exactly. But it would *drop* a card whose `waiting_on` is set yet
   whose `waiting_until` has elapsed (re-entered the queue) — i.e. `--waiting`
   would then mean "currently impeded," not "carries an overlay."

These disagree on the elapsed-`waiting_until` + `waiting_on`-set case, so the
flag's intended meaning ("carries an overlay" vs "is currently impeded") must
be decided before coding. Distinct from `standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits`,
which targets the `standup` skill, not this engine flag — though the chosen
semantics should stay consistent between the two.

## Decision required

**Q: What should `goc --waiting` filter on?**

- **Option A (overlay-field-presence):** `waiting_on is not None or waiting_until is not None`.
  Recommended — matches the documented help text and is a strict superset of
  today's behavior (no card currently shown disappears).
- **Option B (impediment predicate):** `waiting_impedes(t)`. Aligns with
  `--ready`/board, but redefines `--waiting` as "currently impeded" and hides
  elapsed-wait cards (which are arguably the ones an operator most wants to see
  for SLE escalation).

Recommendation: **Option A** — the flag's name and help are about *carrying
the overlay*, and elapsed-wait surfacing is exactly what `--waiting` should
keep showing. Confirm before implementing.

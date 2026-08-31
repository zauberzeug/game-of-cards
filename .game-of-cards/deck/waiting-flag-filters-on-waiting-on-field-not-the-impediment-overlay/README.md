---
title: waiting-flag-filters-on-waiting-on-field-not-the-impediment-overlay
summary: "FIXED IN CODE, AWAITING RATIFICATION — and the shipped answer is this card's Option B, not the Option A it recommended. `goc --waiting` no longer filters on `t.waiting_on is not None`; commit 91d40320 (2026-06-24) routed it through the `waiting_impedes` predicate and fd34c7cc wrapped that in `live_impeded`. So the bare-`waiting_until` deferral this card was filed about is now visible, and the elapsed-`waiting_until` case this card warned Option B would drop is now dropped. Pinned by tests/test_waiting_filter_status_scope.py. The gate blocks any autonomous close, so a human `goc decide` is the one action left."
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

Re-resolved at HEAD on 2026-08-24; the cite this card was filed with is dead.

- Filter: `goc/engine.py:4307` — now `live_impeded(t, include_drafts=...)`
- Live-impediment wrapper: `goc/engine.py:2745` (`live_impeded`)
- Impedance predicate: `goc/engine.py:2696` (`waiting_impedes`)
- Flag help text: `goc/engine.py:3912`
- Regression coverage: `tests/test_waiting_filter_status_scope.py:91`

## What was broken, and what the code does now

The filter used to check one overlay field:

```python
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if t.waiting_on is not None]
```

and the help text described that field rather than the predicate. The
three-axis stuck model defines the stored impediment overlay as `waiting_on`
set **or** a bare `waiting_until`, so a card deferred with `goc wait <title>
--until <future-date>` and **no** `--reason` was hidden from `--ready`,
flagged `⏳` on the board, and yet omitted from `goc --waiting` — the one
view whose purpose is to surface impeded work.

**That code is gone.** `goc/engine.py:4307` now reads:

```python
rows = [t for t in rows if live_impeded(t, include_drafts=include_drafts)]
```

and the help text (`goc/engine.py:3912`) reads "Filter to cards with an
active impediment overlay (a waiting_on reason or an unelapsed
waiting_until)." The bare-deferral card this was filed about is returned.

**The fix took Option B, which this card did not recommend.** Option A
(overlay-field-presence) was the recommendation precisely because it is a
strict superset that drops nothing; the shipped `live_impeded` reading is
Option B plus two further exclusions (terminal status, draft scaffold). So
the second case this card identified is now live behaviour: a card whose
`waiting_on` is set but whose `waiting_until` has **elapsed** no longer
appears under `--waiting`. That is the SLE-escalation view the card argued an
operator most wants; `validate_waiting_overlay` is the surface that still
carries it. Ratifying this card means accepting that trade, and that is the
substance of the decision below — not the bare-deferral bug, which is fixed.

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

**Reduced on 2026-08-24 to: ratify Option B, or restore Option A.** The code
already ships Option B. Nothing is undecided in the engine; what is missing
is a human's name on a semantics that was chosen by a fix for a different
card. No autonomous pass may supply it — `goc status ... superseded` refuses
while `human_gate: decision` and points at `goc decide`.

**Q: What should `goc --waiting` filter on?**

- **Option A (overlay-field-presence):** `waiting_on is not None or waiting_until is not None`.
  Recommended — matches the documented help text and is a strict superset of
  today's behavior (no card currently shown disappears).
- **Option B (impediment predicate):** `waiting_impedes(t)`. Aligns with
  `--ready`/board, but redefines `--waiting` as "currently impeded" and hides
  elapsed-wait cards (which are arguably the ones an operator most wants to see
  for SLE escalation).

Recommendation at filing: **Option A** — the flag's name and help are about
*carrying the overlay*, and elapsed-wait surfacing is exactly what
`--waiting` should keep showing.

**What actually shipped: Option B**, in commit `91d40320` (2026-06-24),
which closed the gate-free card
[goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue](../goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue/)
— filed 2026-06-24, five days after this card, for the same defect — without
referencing this card or writing a supersession edge. The help text was
rewritten to match Option B rather than Option A, so the "matches the help
text literally" argument for A no longer holds: the help text has moved. If
A is still preferred, this card is a live change request against shipped
behaviour, not a bug report. The accumulation pattern is filed separately as
[parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them](../parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them/).

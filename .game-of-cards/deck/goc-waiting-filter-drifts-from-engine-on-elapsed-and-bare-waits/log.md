## 2026-08-24 — hygiene pass: the defect is fixed; only the record is missing

Surfaced by the defunct-citation category of a `Skill(refine-deck)` pass, not
by anyone reading the card. All five cites in the original `## Location` had
died — the anchor text of `filtered = [t for t in filtered if t.waiting_on is
not None]` exists nowhere in the tree. Per the skill's rule, an anchor that
exists nowhere means the cited code was refactored away and the card must be
re-read against HEAD.

**Re-measured.** This card's own `reproduce.py` now reports zero false
positives and zero false negatives across the overlay matrix — the two cells
it was filed on both agree. `tests/test_waiting_filter_status_scope.py`
independently pins the same two cells against the real CLI. The `--waiting`
help text now describes the predicate rather than the storage field.

**Who fixed it.** Commit `91d40320` (2026-06-24) aligned `--waiting` with
`waiting_impedes` while closing
`goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue`, a card filed
at `human_gate: none` that same day for the same defect. Commit `fd34c7cc`
(2026-07-27) then extracted `live_impeded` and routed the flag through it.
Neither referenced this card; no supersession edge was written. This card has
therefore advertised a fixed defect for 61 days.

**Why it is still open.** DoD item 3 asks for the chosen interpretation to be
recorded, and closing requires lowering the gate. `goc status <title>
superseded --by goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue`
was attempted and the engine refused:

```
ERROR: human_gate is 'decision'; run `goc decide ...` to lower the gate
before closing into 'superseded'.
```

That refusal is correct and is why this card cannot be retired by an
autonomous pass. The README dashboard was rewritten in place — Location
re-resolved, the matrix re-scored with an "at filing" column, the decision
section reduced to a ratification — so the remaining human action is one
command. No code changed.

The generalisable finding (a parked card whose defect is fixed elsewhere is
never re-checked, and structurally cannot be retired without a human) is
filed as `parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them`.

## 2026-08-24T05:12:00Z — Staleness re-check

Fixed by `91d40320` (2026-06-24) closing
[`goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue`](../goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue/)
— `goc --waiting` now routes through the `waiting_impedes` predicate instead
of testing `t.waiting_on is not None`, which is exactly the drift this card
reports. `fd34c7cc` (2026-07-27) then extracted `live_impeded` and routed the
flag through it.

Machine-readable restatement of the prose note above, under the greppable
heading `Skill(finish-card)` § "Other cards your fix also fixed" now
prescribes, so a staleness scan can tell a card that was re-read from one
nobody has opened. Retiring this card needs `goc decide`; an agent may not
lower the gate. Tracked by
[`parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them`](../parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them/).

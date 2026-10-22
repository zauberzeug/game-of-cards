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

## 2026-09-14 — refine-deck: defunct cite corrected by hand

The body cited `card_is_ready` at `engine.py:1722`. That number was wrong the
day it was written — at this card's filing commit (`5570bdb4`) `card_is_ready`
was at line 1729, and 1722 was a blank line two lines above an unrelated
function. Because the anchored citation recipe compares the anchor line's text
to HEAD's text at the same offset, and both were blank, three consecutive
hygiene passes verdicted the cite `current` while it drifted 910 lines from the
function it names.

Corrected to `goc/engine.py:2632`, the definition of `card_is_ready` in HEAD.
The recipe gap that hid it is filed as
[citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank](../citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank/),
which carries this cite as its worked example.

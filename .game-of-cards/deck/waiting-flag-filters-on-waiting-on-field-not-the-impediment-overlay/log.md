## 2026-08-24 — hygiene pass: fixed in code, but with the option this card argued against

Surfaced by the defunct-citation category of a `Skill(refine-deck)` pass. The
single cite in `## Location` was dead and its anchor text — `filtered = [t for
t in filtered if t.waiting_on is not None]` — exists nowhere in the tree, so
the card was re-read against HEAD.

**What is fixed.** The bare-`waiting_until` deferral this card was filed
about is now returned by `goc --waiting`: the filter routes through
`live_impeded` (`goc/engine.py:4257`), and
`tests/test_waiting_filter_status_scope.py` pins it.

**What changed the decision.** The fix took **Option B** (the
`waiting_impedes` predicate), not the Option A this card recommended. Two
consequences worth a reader's attention:

1. The elapsed-`waiting_until` case this card flagged as Option B's cost is
   now live behaviour — such a card no longer appears under `--waiting`.
2. Option A's main argument was "matches the help text literally". The help
   text was rewritten by the same commit to describe an active impediment
   overlay, so that argument no longer holds — the help text moved to B.

So if A is still preferred, this card is now a change request against shipped
behaviour rather than a bug report. That reframing is the substance of the
remaining decision, and it is written into the README dashboard in place.

**Who fixed it.** Commit `91d40320` (2026-06-24), closing
`goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue` — filed five
days after this card, at `human_gate: none`, for the same defect, and closed
the same day. No reference to this card and no supersession edge.

**Why it is still open.** Closing requires lowering the gate, which
`goc decide` owns and an autonomous pass may not do; the engine refuses
`goc status ... superseded` while `human_gate: decision`. No code changed.

## 2026-08-24T05:12:00Z — Staleness re-check

Fixed by `91d40320` (2026-06-24) closing
[`goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue`](../goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue/)
— filed five days after this card, at `human_gate: none`, for the same
defect, and closed the same day with no reference and no supersession edge.
Note the engine shipped the predicate reading, i.e. the option this card
argued *against*, so what remains here is a change request against shipped
behaviour rather than a live bug report.

Machine-readable restatement of the prose note above, under the greppable
heading `Skill(finish-card)` § "Other cards your fix also fixed" now
prescribes, so a staleness scan can tell a card that was re-read from one
nobody has opened. Retiring this card needs `goc decide`; an agent may not
lower the gate. Tracked by
[`parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them`](../parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them/).



## 2026-09-19 — 5th instance recorded (no status or gate change)

`standup-waiting-on-you-section-omits-active-cards-parked-at-a-human-gate`
filed and closed today: standup Section 4 gated on
`goc --json --status open`, dropping every card claimed before it was
parked — 5 of 197 live gated cards on this repo's deck. Wired as
`advanced_by` rather than filed as a 5th point-fix proposal.

It is not interchangeable with instances 1-4. Those are Python call
sites that import the engine, so Options A, B and C each retire them.
This one is a shell pipeline in a skill body with no import path; it
was fixed by widening the shipped query, and no helper shape would have
reached it. Recorded as family entry 5 plus a "A caller no helper can
reach" body section so the pending decision can weigh the
non-importing surfaces. The DoD is left untouched — revising it is part
of the decision, not of recording the evidence.

## 2026-10-01T04:53:10Z — Post-decision half handled by a sibling (no status or gate change)

`deciding-a-card-parked-while-active-strands-it-outside-the-pull-queue`
closed today. `goc decide` now returns a card parked while `active` to
`open` in the same write as the gate flip. Before, it left `active` +
`human_gate: none`, which every queue view and pull-card's soft-lock rule
read as a live claim. That card covers what becomes of a parked-`active`
card after the decision. This card's question, how such cards are labelled
while still gated, is unchanged.

One input for the pending decision: Option C's list of status-flip sites
already names `goc decide`, and `goc decide` now has a status transition
of its own (`active → open`). Under Option C it would become
`parked-active → open`.

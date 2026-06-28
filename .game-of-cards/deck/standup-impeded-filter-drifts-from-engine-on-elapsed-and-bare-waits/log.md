# Log

## 2026-06-24 — cross-referenced engine-side sibling

Connected this card to its engine-side sibling,
`goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue` (closed
2026-06-24), which fixed the identical drift in the `goc --waiting`
filter by calling `waiting_impedes(t)` instead of restating
`waiting_on is not None`. Added a "Related — same root shape" section
naming that card plus the OpenClaw TS-port instance
(`openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting`),
and recorded a third fix option in "Possible fixes": now that
`goc --waiting` mirrors `waiting_impedes`, the standup Context block can
delegate to `goc --waiting --json` rather than reimplement the matrix.
No status/gate change — still open, gate decision, awaiting the fix-path
pick.

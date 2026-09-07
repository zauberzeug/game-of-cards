
## 2026-08-31 — refine-deck: stale park re-checked, framing has moved

96 days parked. The collision the card describes is still present, but the
code under it changed and the card's framing is now out of date — recorded
here rather than left for the next reader to rediscover.

`card_cell` (`goc/engine.py:3548-3574`) now applies `⏳` through a single
`not_ready` predicate that unions three axes — `human_gate != "none"`,
`dependency_advisory(..., queue_only=True)`, and `waiting_impedes` — and the
comment above it defends the union explicitly: a gate "parks an open card out
of the pull queue just as hard as an impediment overlay, so it must carry the
same ⏳", with `dependency_blocked` kept deliberately as an advisory
"has an open prereq" hint that does not hide the card. A separate `✎` glyph
was also added for drafts, on the stated reasoning that a distinct hiding
reason deserves a distinct mark.

So the shared glyph is no longer undocumented collateral; it is a stated
design choice, and one of its own justifications (distinct reason → distinct
mark) cuts toward this card. What the card still names correctly is the
residual ambiguity: `dependency_advisory` is advisory and `waiting_impedes`
is queue-hiding, yet they render identically, so the board cannot say "you
may start" versus "do not pull".

Kept parked, `unverified` kept. This is a UX taste call on goc's own surface
with no consultation rubric, which is what the gate is for. A future decision
should argue against the current comment's reasoning, not against the
card's original description of unexamined collateral.

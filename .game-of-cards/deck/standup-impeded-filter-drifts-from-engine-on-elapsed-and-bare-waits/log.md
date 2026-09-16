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

## 2026-09-16T05:03:24Z — Staleness re-check

Commit 6e021a5d (closing
`standup-impeded-section-omits-active-cards-carrying-a-waiting-overlay`)
rewrote the exact line this card is filed against. Two parts of the body
above are now out of date; the defect itself is **not** fixed.

- **Still live.** The block's predicate is still `c.get('waiting_on')`
  truthiness, so both drift cells this card documents — reason with an
  elapsed `waiting_until` (engine has resurfaced it, standup still
  calls it impeded) and a bare future `waiting_until` (engine impedes,
  standup omits) — reproduce unchanged. `reproduce.py` is unaffected:
  every card it writes is `status: open`, so the scope change cannot
  move its verdict.
- **Stale: the citation.** The Context block is at
  `goc/templates/skills/standup/SKILL.md:22`, not line 18, and the
  query is now `--json --status all` with terminal-status and draft
  exclusions beside the truthiness test.
- **Stale: the scope aside.** The "Possible fixes" section offers "add
  `--status open` if this section should stay open-only". It must not:
  Section 2's own prose says a card may appear there while
  `status: active`, and querying the open queue made that impossible.
  The scope is settled and guarded by
  `tests/test_standup_impeded_block_scope.py`. Whichever predicate the
  pending decision picks must keep reporting active impeded cards, and
  must keep excluding terminal and draft ones — if it picks
  `goc --waiting --json`, the engine supplies all three for free.

No status or gate change: the predicate choice is still the human's call.

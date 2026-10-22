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

## 2026-10-22T05:41:25Z — Staleness re-check

6291964e (card `denied-preamble-block-aborts-skill-load-before-the-preflight-routes-to-kickoff`) replaced the standup Section 2 Context block. The hand-rolled `python3 -c` filter over `--json`, which Claude Code would not pre-approve as an `allowed-tools` entry, became the engine's own view: `goc --waiting -v 2>&1 | head -60`. The block now evaluates `waiting_impedes` through `live_impeded` instead of `c.get('waiting_on')`, so the two drifting cells this card describes (elapsed `waiting_until`, bare `waiting_until` without `waiting_on`) can no longer disagree with the engine. `tests/test_standup_impeded_block_scope.py` pins that the block is the `--waiting` view with no re-filter behind it. The gate is `decision`, so retiring this card (done or superseded) is left to the human.

## 2026-10-22T06:00:43Z: decision recorded

Fixed by 6291964e: the standup Section 2 block now asks goc --waiting, the engine's impediment view — Stale sweep under the bulk rule the maintainer approved in a human session on 2026-10-22: the drift no longer reproduces, so the remaining possible fixes are moot. Gate decision → none.

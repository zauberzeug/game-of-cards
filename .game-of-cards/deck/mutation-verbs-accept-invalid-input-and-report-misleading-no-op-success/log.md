## 2026-06-25 — gate raised to `decision` (pull-card)

An autonomous pull-card pass pulled this epic (the only ready card) and
found it is not drainable autonomously: DoD item 1 is a shared-shape
API-contract taste call, and all eight `advanced_by` children carry
their own `human_gate: decision`. No project-local consultation hook is
defined (`.game-of-cards/hooks/pull-card.md` is empty), so per the
pull-card Andon contract the gate was raised to `decision` rather than
guessing the contract.

Added a `## Decision required` section recording the three candidate
shapes (strict-refuse exit 2 / exit-0 stderr WARNING / honest no-op
success line) plus the factoring sub-decision, and surfaced the strong
codebase-internal default: `_cmd_advance` already strict-refuses the
self-target and cycle cases (`engine.py:5233`, `:5237`) and the engine
uniformly uses `goc: error: …` + `sys.exit(2)` for invalid input
(`:2496`, `:2510`, `:3437`, …). Recommended strict-refuse so the
shared-shape decision is a quick confirmation, not an open design space.

No code changed. The eight children remain open; this epic is parked
awaiting the shared-shape decision.

## 2026-08-26T04:43:42Z: ninth child wired — goc-wait-with-a-past-until-date-leaves-the-card-in-the-queue

An audit pass (queue empty of `human_gate: none` work) found a new instance
of this family and wired it in rather than filing it beside the epic:
`goc wait <t> --until <date already elapsed>` writes the overlay, prints the
same success line a live wait gets, and auto-commits — while
`waiting_impedes` reads the elapsed `waiting_until` as non-impeding, so the
card stays in `--ready` and out of `--waiting`. The everyday form is a bare
`--until <today>`: `_waiting_until_instant` resolves `YYYY-MM-DD` to midnight
UTC, so it is elapsed at every moment of the day it names.

Dashboard updated in place: the roster gained a bullet, and the eight-child
counts in the summary, DoD item 2, `## Decision required` and `## Why it
matters` now read nine. The "found these eight" sentence under
`## How this card was surfaced` is left at eight — it describes what the
2026-06-25 refine-deck pass saw, not the current roster.

Also corrected a stale claim in `## Scope notes`: it still said "This epic is
filed at `human_gate: none`" while the frontmatter has read `decision` since
the 2026-06-25 pull-card pass raised it (as `## Decision required` already
recorded). Rewritten in place to state the gate history rather than contradict
the frontmatter.

No code changed. The shared-shape decision remains the blocker for all nine.

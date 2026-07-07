---
title: heaviest-skills-re-load-full-methodology-briefing-per-card-cycle
summary: "Every autonomous-loop card cycle invokes `create-card` (328 lines) + `finish-card` (352 lines) = ~680 lines of skill body, plus cross-references into `card-schema` (826 lines). The full bodies contain methodology framing (XP/Kanban citations, philosophy, antipatterns, decision-gate body contracts) that a cold reader or new agent needs once, but that the autonomous loop has internalized after the first card of the day. Across the recent 59-card batch, that briefing was re-loaded ~59 times. This card scopes a lean/full split: a small per-skill `<verb>-lean` surface that the autonomous loop uses, and the current full surface preserved for deliberate, human-paced or first-time use. The lean/full boundary itself is the open design question — what stays in lean, what only the full briefing keeps."
status: open
stage: null
contribution: medium
created: "2026-05-28T04:02:24Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, infra, documentation]
definition_of_done: |
  - [ ] PROCESS: the lean/full boundary is decided for each in-scope skill (`create-card`, `finish-card`, `advance-card`, `card-schema`) and recorded in `## Decision` body section — which sections stay in lean, which move to full-only.
  - [ ] PROCESS: the routing mechanism is decided (see Decision required, item 2) and recorded.
  - [ ] PROCESS: the `card-schema` reference split is decided (see Decision required, item 3) and recorded.
  - [ ] MECHANICAL: lean variants land at `goc/templates/skills/<verb>-lean/SKILL.md` for the four in-scope skills. Each is ≤ 80 lines and carries the verb mechanics, the DoD-method-tag enum, the parallel-agent commit guard (for finish-card-lean), and a one-line pointer to the full skill.
  - [ ] MECHANICAL: auto-invoke triggers route correctly per the decided mechanism. The full skill remains the default for user-typed invocations and first-of-day calls; the lean variant is used by `/loop`, `pull-card`, and same-day-filed bug-class closures.
  - [ ] EMPIRICAL: a representative autonomous-loop card cycle re-run with the lean skills shows a measured reduction in skill-body lines loaded per cycle (target: ≥ 70% reduction on `create-card` + `finish-card` aggregate). Recorded in `log.md`.
  - [ ] EMPIRICAL: a deliberate, human-paced invocation (e.g., user-typed "let's do X" → `create-card`) still loads the full skill body; the lean variant is invisible in that flow. Verified by inspection.
  - [ ] PROCESS: only `goc/templates/skills/` is hand-edited; `python scripts/sync_plugin_assets.py --check` passes (mirrors regenerated for the new lean SKILL.md files).
  - [ ] PROCESS: `uv run goc validate` passes; `validate_skill_dir_parity` is extended to recognize the lean variants or explicitly exclude them per the chosen mechanism.
---

# heaviest-skills-re-load-full-methodology-briefing-per-card-cycle

## What's heavy

Skill body sizes that re-load per invocation:

| Skill | Lines |
|---|---:|
| `card-schema` | 826 |
| `advance-card` | 354 |
| `finish-card` | 352 |
| `refine-deck` | 336 |
| `create-card` | 328 |
| `audit-deck` | 239 |
| `standup` | 143 |
| `pull-card` | 124 |

A single autonomous card cycle invokes `create-card` + `finish-card` (≈ 680 lines), and several of those bodies cross-reference `card-schema` (826 lines). Most of the body is **methodology framing** — XP/Kanban citations, philosophy ("a card is a self-contained briefing for the next reader"), the title-antipattern guard rationale, the decision-gate body contract, the rich-artifact escape hatch, the parallel-agent commit safety section. All of that is essential for a cold reader, a new agent on its first card, or a deliberate user-typed invocation. None of it is information the autonomous loop needs on its 50th iteration of the day.

## Why human_gate=session

The lean/full boundary is the substantive question, not the mechanism. Three credible cuts of "what's lean" exist and they imply different methodology bets; see `## Decision required` below.

## Decision

*Resolved 2026-07-07T04:04:48Z:* Adopt progressive disclosure inside each skill (happy-path SKILL.md core + on-demand reference.md sibling) instead of lean/full skill variants; supersede this card by plugin-skills-consume-a-third-of-downstream-session-usage

*Reasoning:* A downstream plugin-usage report (31% of session usage, finish-card alone 15%) shows deliberate human-paced use pays the same per-invocation cost as autonomous loops, so there is no audience for a fat default variant and the lean/full routing question dissolves

## Why it matters

Recent 59-card batch ≈ 59 × 680 lines = ~40,000 lines of skill body re-loaded just for `create-card` + `finish-card` (before counting cross-references into `card-schema`, `advance-card`, or the bash subprocess outputs in Context blocks). This is the single largest per-cycle token cost we can identify; sibling card `trim-token-cost-of-autonomous-card-cycles` covers everything else, but those wins are individually small. This card is where the bulk of the savings live.

## Cross-references

- `trim-token-cost-of-autonomous-card-cycles` — sibling umbrella for the small mechanical wins.
- `audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings` — sibling session-gated card on the orthogonal axis (card count, not skill body size).
- The recent 59-card autonomous batch is the motivating evidence.

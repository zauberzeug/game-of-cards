---
title: polish-persona-section-headline-and-accepts-alignment
summary: "Polish the website's three-persona section after first ship: each card's headline must fit on a single line so all three sit on the same horizontal baseline, the redundant 'PRIMARY AUDIENCE' chip is removed (the gold left-border already differentiates primary from secondary), and the three 'Accepts:' lines should align across cards instead of breaking at three vs two lines."
status: done
stage: null
contribution: low
created: 2026-05-08
closed_at: 2026-05-08
human_gate: none
advances:
  - define-personas-and-use-cases-for-game-of-cards
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] All three persona-card headlines render on a single line at desktop width (1280px viewport) — currently "The multi-agent coordinator" wraps to two lines because the h3 font-size is too large for the column
  - [x] The "PRIMARY AUDIENCE" badge is removed; primary persona is signalled by the existing brighter gold left-border + subtle background lift
  - [x] The three "Accepts: …" lines end at roughly the same vertical position across all three cards (rebalance copy length where needed; don't force equal heights with min-height hacks)
  - [x] Mobile layout still stacks cleanly (single column at <860px), no regressions
  - [x] Playwright capture + Rodja visual sign-off before close (per UI-verification rule)
  - [x] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Polish persona section headline and accepts alignment

## Why

The persona section shipped as part of `define-personas-and-use-cases-for-game-of-cards` (closed 2026-05-08). After ship, three small layout issues are visible at desktop width:

1. **Headlines mis-align.** "The vibe-coder" and "The solo developer" are one line each; "The multi-agent coordinator" wraps to two lines at 22px Cormorant SC inside a ~315px column, pushing the rest of that card's content one row down. The cards no longer share a horizontal baseline.

2. **Redundant primary signal.** The "PRIMARY AUDIENCE" chip on the vibe-coder card duplicates information the brighter gold left-border already conveys. Two markers for one signal feels heavy.

3. **"Accepts" lines mis-align.** The three Accepts paragraphs differ in length — vibe-coder's wraps to two lines, the other two to three lines — so the bottom edges of the cards don't align even though the layout uses `flex: 1` to push the trade-off block to the bottom. The fix is content rebalancing (tighten the longer Accepts), not a CSS height hack.

## Approach

- Drop h3 font-size from 22px to 18px so the longest title (`The multi-agent coordinator`) fits on one line at desktop width.
- Remove the `<span class="persona-badge">PRIMARY AUDIENCE</span>` element and its CSS rule.
- Rebalance the three Accepts trade-off lines to similar word counts so the natural wrap matches across cards.
- Verify on desktop (1280×900) and mobile (390×844) viewports.

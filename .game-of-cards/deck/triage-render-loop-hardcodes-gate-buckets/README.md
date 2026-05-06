---
title: triage-render-loop-hardcodes-gate-buckets
summary: "`goc triage` selects parked cards via `human_gate != 'none'` (correct), but the text-mode render loop only emits buckets for `'decision'` and `'session'` literally. Schema currently allows only those two non-`none` values, so the bug is latent: any future or migration-introduced gate value would be counted in the `Waiting on you (gate ≠ none)` header but never rendered. Unverified: not currently reachable through the supported schema; surfaces only after the open card `support-custom-card-workflows-and-statuses` adds gate values, or a hand-edit slips in. Park as a sentinel against forward drift."
status: open
stage: null
contribution: low
created: 2026-05-06
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, unverified, api-contract]
definition_of_done: |
  - [ ] (replace with real criteria)
---

# triage-render-loop-hardcodes-gate-buckets

## Hypothesis

In `goc/engine.py` (per agent report, ~lines 1972-2025), `triage` selects with `human_gate != 'none'` but renders with a hard-coded `for gate in ("decision", "session"):` loop. Cards with any other non-`none` gate are counted in the header but never rendered in text mode.

The selection / render pair is consistent with the schema today (`schema.yaml` lists `none | decision | session`), so it is currently unreachable through the supported API. The agent flagged it as forward-looking: the open card `support-custom-card-workflows-and-statuses` is meant to extend gate values, and any future migration adding a value would silently lose visibility in `triage` until the render loop is updated.

## Why deferred (unverified)

- The defect is latent today — schema rejects any value outside `{none, decision, session}`.
- Reproducing requires hand-editing a card's frontmatter to bypass the schema, which `goc validate` will then reject. Not a clean reproducer until the schema permits more gates.
- Promotion path: revisit when `support-custom-card-workflows-and-statuses` lands (or any other change extends the gate enum). The fix at that point is mechanical — drive the bucket loop off `sorted(by_gate.keys())` instead of a literal tuple.

## Falsification recipe

1. Confirm the literal-tuple shape is still in `engine.py` triage render loop.
2. Add a third value to the gate enum (or hand-edit a card and bypass validate); compare `goc triage` text output to `goc triage --json`. The header counts must agree with the body buckets across both modes.
3. Either the loop is generic now (mark this card disproved) or the latent bug is reachable (promote with a real reproduce.py).

## Surfaced by

`extend-deck` round 2 hunt (general-purpose agent, candidate #3 of 3).

---
title: verdict-coherence-check-mistakes-the-disproved-status-name-for-a-negative-verdict
summary: "DECISION_CONTRADICTS_VERDICT fires when a summary merely names the status disproved (NEGATIVE_VERDICT_RE matches the bare word) and the decision uses everyday words like 'no longer' or 'instead of' (RESCOPE_MARKERS_RE). A human-session decision round on 2026-10-22 hit it on five cards and had to reword them to get validate quiet."
status: active
stage: null
contribution: medium
created: "2026-10-22T06:03:27Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, unverified]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — a summary that only names the status (`flips to \`disproved\``, "or the card is disproved") next to a decision containing "no longer" or "instead of" raises no DECISION_CONTRADICTS_VERDICT, while a genuine "REFUTED"/"do not pursue" summary over a reversing decision still does
  - [ ] TDD: a unittest pins both directions (planted false positive stays silent, planted true positive still warns)
  - [ ] MECHANICAL: drop the `unverified` tag once reproduce.py lands
  - [ ] PROCESS: `uv run goc validate` passes and the suite is green
worker: {who: "claude[bot]", where: main}
---

# The verdict-coherence check mistakes the disproved status name for a negative verdict

## Location

- `goc/engine.py:707-711` — `RESCOPE_MARKERS_RE`: `re-?scop\w*|supersed\w*|revers\w*|overturn\w*|no longer|instead of|was wrong|now\s+viable|actually\s+viable`.
- `goc/engine.py:719-723` — `NEGATIVE_VERDICT_RE`: `refuted|disproved|disproven|unviable|not viable|do not pursue|…`.
- `goc/engine.py:2648` — `validate_decision_verdict_coherence`, which warns when a resolved `## Decision` matches the first and a summary/banner/DoD surface matches the second.

## What's broken

The two token lists are built for a narrow situation — a "REFUTED" summary left standing over a decision that reverses it. But `disproved` is also a status name that ordinary summaries and DoD lines mention ("…or the run disproves the hypothesis and the card flips to `disproved`"), and "no longer", "instead of" and "supersede" are everyday words in decisions that reverse nothing. Both lists match on those ordinary uses, so the advisory fires on cards whose verdict is perfectly coherent.

## Empirical evidence (to be reproduced)

During the human-session decision round on 2026-10-22, recording decisions on hub epics and their children raised `DECISION_CONTRADICTS_VERDICT` on five cards; the deciding agent silenced it by rewording the decisions, not because the cards contradicted themselves. No reproducer exists yet (hence `unverified`). Recipe: a scratch deck with one card whose summary says "the card flips to `disproved` if the probe fails", decided with `--decision "Use the helper instead of the inline check"` — expect the warning today, none after the fix; plus a control card whose summary says "REFUTED: do not pursue" decided with "Reverse: now viable" — expect the warning before and after.

## Why it matters

An advisory that cries wolf trains deciders to reword decisions until it goes quiet, which hides the real self-contradictions it exists for, and it makes `goc decide` look unreliable in exactly the bulk decision rounds the deck now needs.

## Fix

Tighten the pattern, not the surfaces: exclude status-name mentions of `disproved` (backticked, or after "flips to"/"status"/"as") from `NEGATIVE_VERDICT_RE`, and drop the bare everyday markers (`no longer`, `instead of`) from `RESCOPE_MARKERS_RE` or require them near a verdict word. Keep both directions under test.

Related: [goc-decide-leaves-stale-verdict-content-when-recording-a-rescope](../goc-decide-leaves-stale-verdict-content-when-recording-a-rescope/) (introduced the check), [decision-verdict-coherence-check-skips-rubric-derived-decision-headings](../decision-verdict-coherence-check-skips-rubric-derived-decision-headings/).

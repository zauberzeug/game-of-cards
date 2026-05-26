---
title: compute-values-inherits-value-through-done-and-superseded-descendants
summary: "`compute_values`'s Bellman recursion `value(c) = rank(c) + γ·max(value(d) for d in advances(c))` applies no terminal-status filter to the descendant `d`. An open card that advances an already-`done` (or `superseded`) card still inherits that descendant's full rank, so completed work amplifies a live card's priority even though it can no longer be unblocked. May be intended (chain depth as a curation signal) or a gap (the deck doc says the scheduler walks `advances` across *live* cards). UNVERIFIED — needs a decision + reproduce.py."
status: done
stage: null
contribution: medium
created: "2026-05-26T20:56:27Z"
closed_at: 2026-05-26T21:18:51Z
human_gate: none
advances: []
advanced_by: []
tags: [api-contract]
definition_of_done: |
  - [x] PROCESS: decide whether descendants with a terminal status should contribute to the scheduler value — record the decision and its rationale in log.md (cross-ref the deck-as-scheduler-vs-record contract in AGENTS.md).
  - [x] TDD: reproduce.py demonstrates the current value an open→done chain yields, and (if the decision is "exclude terminal descendants") asserts the corrected value.
  - [x] MECHANICAL: if excluding, `value_for` skips descendants whose status is terminal (or the caller pre-filters); the docstring is updated to state the live-only rule explicitly.
  - [x] PROCESS: drop the `unverified` tag once the decision is recorded and (if applicable) the fix lands.
worker: {who: "claude[bot]", where: main}
---

# `compute_values` inherits value through `done` / `superseded` descendants

## Location

`goc/engine.py:1593-1625` (`value_for`, the inner recursion of
`compute_values`). Called on the full deck (`load_all_cards()`), so
closed cards participate as descendants.

## Hypothesis / question (UNVERIFIED)

The recursion has no terminal-status check on the descendant:

```python
for dest in t.frontmatter.get("advances") or []:
    if dest not in by_title:
        ... # dangling warn
        continue
    d_value, d_path = value_for(dest, in_progress)
    if d_value > best[0]:
        best = (d_value, [dest, *d_path])
```

So an `open low` card A with `advances: [B]` where B is `done high`
scores `1.0 + 0.7·9.0 = 7.3` — outranking a genuinely-open `medium`
(3.0) purely on the strength of work that is already complete and can
no longer be unblocked.

The deck-as-scheduler contract in `AGENTS.md` states: "The scheduler
axis walks `advances` edges across **live** cards." That phrasing
suggests terminal descendants should NOT contribute to the scheduling
value. But the `compute_values` docstring frames chain depth as "a
curation signal" without restricting it to live descendants, so this
may be deliberate. **This card is the decision + (conditional) fix**,
not a presumed bug.

## Why deferred / why a decision gate is implied

The core question — should completed work amplify a live card's
priority? — is an api-contract judgement, not a mechanical fix. It
also interacts with the record-axis design (closed-card edges are
first-class for history). No reproduce.py budget this round.

## Falsification / demonstration recipe

`compute_values([A(low, open, advances=[B]), B(high, done)])["A"]`
prints `(7.3, ["B", "self"])` today. If the decision is live-only,
expected `(1.0, ["self"])`. Decide first; the assertion direction
follows the decision.

Surfaced by the engine-core defect hunter during an audit-deck round.

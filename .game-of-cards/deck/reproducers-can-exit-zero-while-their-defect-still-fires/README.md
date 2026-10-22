---
title: reproducers-can-exit-zero-while-their-defect-still-fires
summary: "Two reproduce.py scripts exited 0 only while their drift still fired, the reverse of the DoD convention 'reproduce.py exits zero (defect no longer fires)', so after the fix they failed and before it they would have ticked the box on a live defect. Neither create-card nor card-schema states the exit-code contract, so each reproducer picks its own."
status: open
stage: null
contribution: medium
created: "2026-10-22T06:07:58Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [meta-fix, documentation]
definition_of_done: |
  - [ ] MECHANICAL: `Skill(create-card)` Step 6 and `Skill(card-schema)` state the reproducer exit-code contract — 0 = defect no longer fires, 1 = defect fires, 2 = the harness or a precondition is broken — matching the DoD convention
  - [ ] EMPIRICAL: every open or gated card's reproduce.py is classified against the contract (a static scan for a `return 0` on the defect-present branch, confirmed by running the suspects); inverted ones are listed in log.md and fixed or re-filed
  - [ ] TDD: a guard (test or validate warning) catches a planted reproducer that returns 0 on its defect-present branch, if a reliable static signal exists; otherwise the card records why the contract stays documentation-only
  - [ ] PROCESS: `uv run goc validate` passes
---

# Reproducers can exit zero while their defect still fires

## Location

- `.game-of-cards/deck/goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits/reproduce.py` and `.game-of-cards/deck/standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits/reproduce.py` — both ended with `print("DRIFT REPRODUCED" if …)` and `return 0` on the defect-present branch, until 7616adc2 (2026-10-22) switched them to the post-fix contract.
- `goc/templates/skills/create-card/SKILL.md` Step 6 — says a reproducer "prints output an outside reader would accept as proof", and the DoD scaffold says `TDD: reproduce.py exits zero (defect no longer fires)`, but no sentence states what each exit code means.

## What's broken

The DoD convention reads exit 0 as "fixed". A reproducer written as "succeed when you reproduce the bug" inverts that: before the fix it exits 0 (a closer could tick the TDD box on a live defect), after the fix it exits 1 (the closing agent sees a failure on a fixed card). The stale sweep on 2026-10-22 found both cases among 38 anchor-stale cards; one of the two also hard-coded the old filter instead of reading the template, so it could never pass.

## Why it matters

Exit codes are what unattended agents and future guards act on — the parked-decision re-check (Option B, a refine-deck category that re-runs reproduce.py) will read them by the dozen. An unstated contract makes every such run ambiguous.

Related: [parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them](../parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them/), [create-card-and-deck-skills-claim-goc-new-scaffolds-a-reproduce-py-stub](../create-card-and-deck-skills-claim-goc-new-scaffolds-a-reproduce-py-stub/).

---
title: occasional-goc-skills-still-load-full-manuals
status: open
stage: null
contribution: low
created: "2026-07-07T04:32:43Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation]
summary: |-
  The progressive-disclosure split (happy-path SKILL.md core + on-demand
  reference.md sibling) landed only for the five hot-path skills. deck
  (15,984 B), refine-deck (15,124 B), kickoff (13,058 B), and audit-deck
  (11,558 B) still ship their full manuals on every load. They fire far
  less often — hence low contribution — but the same restructure applies,
  and deck's description advertises session-start auto-invocation, so its
  16 KB may load more often than the downstream usage report suggested.
definition_of_done: |
  - [ ] MECHANICAL: deck, refine-deck, audit-deck, and kickoff SKILL.md restructured to happy-path core + `reference.md` sibling, same no-guidance-deleted rule as the hot-path pass (every moved section lands in the sibling with a routing pointer).
  - [ ] TDD: the four skills are added to `tests/test_skill_body_size.py` BODY_CAPS with caps they meet after the restructure (red before, green after).
  - [ ] EMPIRICAL: before/after byte counts recorded in log.md.
  - [ ] PROCESS: sync + porter --check green; `uv run goc validate` and the regression suite pass.
---

# Occasional GoC skills still load full manuals

## Location

`goc/templates/skills/{deck,refine-deck,kickoff,audit-deck}/SKILL.md`.

## What's broken

The pattern card
([`plugin-skills-consume-a-third-of-downstream-session-usage`](../plugin-skills-consume-a-third-of-downstream-session-usage/))
restructured the five hot-path skills for progressive disclosure and
capped them in `tests/test_skill_body_size.py`. Four skills stayed out
of scope because they did not appear in the downstream usage report's
top five:

| Skill | body size |
|---|---:|
| deck | 15,984 B |
| refine-deck | 15,124 B |
| kickoff | 13,058 B |
| audit-deck | 11,558 B |

Each still ships its complete manual per load. They are
lower-frequency surfaces (hygiene passes, first-time setup, the
methodology front door), which is why this card is `contribution:
low` — but `deck`'s own description says "AUTO-INVOKE … at session
start as a reminder", so in repos where that trigger actually fires,
its 16 KB is a per-session cost, not a rare one.

## Fix

Apply the identical split: happy-path core in SKILL.md, edge cases and
methodology rationale in a sibling `reference.md` with a routing
table; then extend the `BODY_CAPS` guard so the four bodies cannot
re-fatten. The mechanism (install asset walk, plugin syncs, OpenClaw
porter sibling copy) is already proven by the pattern card — this is a
repeat application, no new machinery.

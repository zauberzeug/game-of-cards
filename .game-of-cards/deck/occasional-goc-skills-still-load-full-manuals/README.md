---
title: occasional-goc-skills-still-load-full-manuals
status: done
stage: null
contribution: low
created: "2026-07-07T04:32:43Z"
closed_at: "2026-07-11T01:06:09Z"
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation]
summary: |-
  RESOLVED: the progressive-disclosure split (happy-path SKILL.md core +
  on-demand reference.md sibling) originally landed only for the five
  hot-path skills; deck (15,984 B), refine-deck (15,410 B), kickoff
  (13,058 B), and audit-deck (11,558 B) still shipped their full manuals
  on every load. The same restructure is now applied to all four (cores:
  9,910 / 9,810 / 10,397 / 9,631 B) and BODY_CAPS in
  tests/test_skill_body_size.py guards them against re-fattening.
definition_of_done: |
  - [x] MECHANICAL: deck, refine-deck, audit-deck, and kickoff SKILL.md restructured to happy-path core + `reference.md` sibling, same no-guidance-deleted rule as the hot-path pass (every moved section lands in the sibling with a routing pointer).
  - [x] TDD: the four skills are added to `tests/test_skill_body_size.py` BODY_CAPS with caps they meet after the restructure (red before, green after).
  - [x] EMPIRICAL: before/after byte counts recorded in log.md.
  - [x] PROCESS: sync + porter --check green; `uv run goc validate` and the regression suite pass.
worker: {who: "claude[bot]", where: main}
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

## Fix (applied)

The identical split is applied: each of the four skills now has a
happy-path core SKILL.md and a sibling `reference.md` carrying the
moved sections behind a routing table (no guidance deleted). The four
skills are added to `BODY_CAPS` in `tests/test_skill_body_size.py` —
`deck`/`refine-deck`/`audit-deck` at 10,000 B, `kickoff` at 11,000 B
(its body is mostly verbatim user-facing dialog that cannot move to
the sibling). Resulting core sizes: deck 15,984 → 9,910 B; refine-deck
15,410 → 9,810 B; kickoff 13,058 → 10,397 B; audit-deck 11,558 →
9,631 B. The install asset walk, plugin syncs, and OpenClaw porter
sibling copy picked the new `reference.md` files up with no new
machinery, as the pattern card predicted.

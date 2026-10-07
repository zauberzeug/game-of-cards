---
title: kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe
summary: "UNVERIFIED. Kickoff Stage 6 records an autonomy mode (loop, cron, action) and tells the user the host complement provides the host-specific recipe, but none of claude-kickoff, codex-kickoff or openclaw-kickoff mentions autonomy, /loop, cron or a workflow file, and no code reads the recorded key. Picking a mode therefore sets nothing up, contrary to the 2026-05-10 decision on kickoff-offers-autonomy-setup-options that complements carry the recipes."
status: active
stage: null
contribution: medium
created: "2026-09-28T01:33:42Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py scans the shipped host complements (`claude-kickoff`, `codex-kickoff`, `openclaw-kickoff`) for a recipe per `autonomy:` mode and asserts every mode kickoff Stage 6 offers has one — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] MECHANICAL: each host complement carries the recipe for every mode Stage 6 offers (`loop`, `cron`, `action`) on that host, or kickoff Stage 6 stops promising one and states what the recorded `autonomy:` key does
  - [ ] MECHANICAL: drop the `unverified` tag once reproduce.py lands; append a post-close pointer to `kickoff-offers-autonomy-setup-options/log.md`
worker: {who: "claude[bot]", where: main}
---

# Kickoff's autonomy choice hands off to host complements that carry no recipe

> **UNVERIFIED.** Surfaced by an audit hunter on the shipped-skills-vs-CLI
> seam on 2026-09-28. The filing agent re-read and confirmed the
> citations. No `reproduce.py` was written this round; the falsification
> recipe is below.

## Location

- `goc/templates/skills/kickoff/SKILL.md:192` "Stage 6 — pick an autonomy
  mode". It offers manual, supervised loop, local cron, CI / GitHub
  Action, and skip.
- `goc/templates/skills/kickoff/SKILL.md:216-218` records the answer "as a
  top-level `autonomy:` key with one of these values: `manual`, `loop`,
  `cron`, `action`".
- `goc/templates/skills/kickoff/SKILL.md:222-226`:
  > If the host has its own kickoff complement (Claude Code ships
  > `claude-kickoff`, OpenClaw ships its own equivalent when present),
  > invite the user to run it now — the complement provides the
  > host-specific recipe for the chosen mode (e.g., wiring `/loop`,
  > suggesting a cron line, or scaffolding a workflow file).
- The three complements, `claude-kickoff/SKILL.md` (177 lines),
  `codex-kickoff/SKILL.md` (161) and `openclaw-kickoff/SKILL.md` (113),
  contain no occurrence of `autonomy`, `/loop`, `cron`, `schedule` or
  "workflow file". The only related hit is a passing mention of
  `pull-card` at `openclaw-kickoff/SKILL.md:113`.
- No Python in `goc/` reads the `autonomy:` key. Its only reader is
  kickoff's own Stage 0 re-run check (`kickoff/SKILL.md:42`).

## Hypothesis

A user who picks option 2, 3 or 4 is sent to a complement that has
nothing for them. The mode is recorded and nothing sets it up:

- no `/loop` wiring;
- no cron line;
- no workflow scaffold.

The closed card
[kickoff-offers-autonomy-setup-options](../kickoff-offers-autonomy-setup-options/)
resolved on 2026-05-10 that "host complements provide host-specific
recipes" (its README line 79). None of its DoD items covered the
complements, and the hunter found no commit touching `autonomy`, `/loop`
or `cron` in any complement since.

## Why deferred

The citations are confirmed by grep. Whether the fix lands the recipes in
the complements or narrows kickoff's promise is left to the card's worker,
and no `reproduce.py` is committed this round.

## Fix direction

Recommended: give each complement one short section per offered mode. On
Claude Code these are the `/loop /pull-card <interval>` invocation, the
cron line that runs a headless `pull-card` session, and a pointer to a
GitHub Actions workflow shape. This repo's own `.github/workflows/pull-card.yml`
is a worked example of that shape. Where a host genuinely has no recipe
for a mode, kickoff's hand-off sentence should say so rather than promise
one.

## Falsification recipe

`grep -n -i -E "autonomy|/loop|cron" goc/templates/skills/*-kickoff/SKILL.md`.
If every offered mode has a recipe in its host's complement, the
hypothesis is disproved.

Surfaced by: general-purpose audit hunter (shipped skills vs CLI
contract), 2026-09-28.

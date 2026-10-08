---
title: kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe
summary: "FIXED. Kickoff Stage 6 recorded an autonomy mode (loop, cron, action) and told the user the host complement provides the host-specific recipe, but none of claude-kickoff, codex-kickoff or openclaw-kickoff mentioned autonomy, /loop, cron or a workflow file, and no code reads the recorded key, so picking a mode set nothing up (reproduce.py: 9 of 9 mode recipes missing). Each complement now carries an autonomy-recipes section with one entry per mode, saying so where the host has no recipe, and Stage 6 states that the key is a record only. tests/test_kickoff_autonomy_recipes.py guards the coverage."
status: done
stage: null
contribution: medium
created: "2026-09-28T01:33:42Z"
closed_at: "2026-10-08T04:43:52Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: a reproduce.py scans the shipped host complements (`claude-kickoff`, `codex-kickoff`, `openclaw-kickoff`) for a recipe per `autonomy:` mode and asserts every mode kickoff Stage 6 offers has one — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] MECHANICAL: each host complement carries the recipe for every mode Stage 6 offers (`loop`, `cron`, `action`) on that host, or kickoff Stage 6 stops promising one and states what the recorded `autonomy:` key does
  - [x] MECHANICAL: drop the `unverified` tag once reproduce.py lands; append a post-close pointer to `kickoff-offers-autonomy-setup-options/log.md`
worker: {who: "claude[bot]", where: main}
---

# Kickoff's autonomy choice hands off to host complements that carry no recipe

> **Confirmed, then fixed (2026-10-08).** Surfaced by an audit hunter on
> the shipped-skills-vs-CLI seam on 2026-09-28. `reproduce.py` in this
> directory confirmed it before the fix: 9 of 9 mode recipes missing,
> with all three modes absent from all three complements. It exits 0
> after the fix. See § Resolution; the sections below describe the
> pre-fix state.

## Resolution

Both branches of the fix direction landed. The recipe branch covers the
modes a host supports, and the honest-statement branch covers the rest.

- **Complements.** `claude-kickoff`, `codex-kickoff` and `openclaw-kickoff`
  each gained a `## Reference: autonomy recipes` section with one
  `- **`<mode>`**` entry for each of `loop`, `cron` and `action`. Their
  confirm-ready stage now shows the user the entry for the mode recorded
  in `config.yaml`.
  - Claude Code: `/loop 30m /pull-card`, a `claude -p` crontab line, and
    a `claude-code-action` workflow pointing at this repo's
    `pull-card.yml` as a worked example.
  - Codex: ChatGPT desktop scheduled tasks for `loop`, and a `codex exec`
    crontab line for `cron`, with the read-only-`.git` sandbox caveat.
    `action` says no recipe ships: `codex-action`'s default sandbox keeps
    `.git` read-only.
  - OpenClaw: `/loop` and `openclaw automations create`. `action` says no
    recipe ships, because OpenClaw has no official GitHub Action.
- **Kickoff Stage 6.** It now says the `autonomy:` key is a record, not
  a setup (no goc command reads it; only Stage 0's re-run check does). It
  names all three complements and promises their recipes "say so where
  the host has none". The example became the documented interval-first
  form `/loop 30m /pull-card`; Claude Code only parses a trailing
  interval as a clause like `every 2 hours`. The `config.yaml` template
  comment changed in lockstep.
- **Guard.** `tests/test_kickoff_autonomy_recipes.py` fails when a
  complement lacks an entry for any mode Stage 6 records (complements
  are discovered by glob) or when Stage 6 stops naming one.
- **Sources.** The host facts come from official docs fetched on
  2026-10-07 by the prior, turn-capped session on this card: Claude Code
  scheduled-tasks, headless and github-actions pages; ChatGPT/Codex
  non-interactive-mode, automations and github-action pages; OpenClaw
  cli/cron, automation and slash-commands pages. Recipes stay to the
  documented flags. Skill invocation is phrased in plain language
  wherever a host does not document skill expansion inside scheduled
  prompts.

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

## Falsification recipe

Run `python3 reproduce.py` from this directory. It reads the modes that
Stage 6 records, `manual` excepted, then looks for one
`- **`<mode>`**` entry per mode in the autonomy section of each
`goc/templates/skills/*-kickoff/SKILL.md`. It exits 1 and names the gaps
when any entry is missing, and exits 0 when all are present. The
original grep-level check was
`grep -n -i -E "autonomy|/loop|cron" goc/templates/skills/*-kickoff/SKILL.md`.

Surfaced by: general-purpose audit hunter (shipped skills vs CLI
contract), 2026-09-28.

---
title: float-autonomous-workflows-back-to-opus-alias
summary: "The three autonomous-agent workflows (pull-card, audit-deck, refine-deck) run on `--model claude-fable-5`; the fleet should move to the Opus tier. Use the floating alias `--model opus` rather than a pinned `claude-opus-5` so future Opus releases are picked up without a YAML edit. Reverses re-pin-autonomous-workflows-to-fable-5-after-re-enable and restores the policy of float-opus-alias-on-autonomous-github-workflows."
status: done
stage: null
contribution: low
created: "2026-07-25T04:37:15Z"
closed_at: "2026-07-25T04:39:26Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [x] MECHANICAL: `.github/workflows/pull-card.yml` passes `--model opus` in `claude_args`
  - [x] MECHANICAL: `.github/workflows/audit-deck.yml` passes `--model opus` in `claude_args`
  - [x] MECHANICAL: `.github/workflows/refine-deck.yml` passes `--model opus` in `claude_args`
  - [x] MECHANICAL: `grep -rn -- "--model" .github/workflows/` shows no remaining `claude-fable-5` override
  - [x] PROCESS: closed predecessor card re-pin-autonomous-workflows-to-fable-5-after-re-enable amended with a forward pointer to this card
worker: {who: Rodja Trappe, where: main}
---

# float-autonomous-workflows-back-to-opus-alias

Move the three cron-driven autonomous agents off Claude Fable 5 and
back onto the Opus tier, using the floating `opus` alias so the fleet
tracks each Opus release without a manual workflow edit.

## Location

- `.github/workflows/pull-card.yml:101` — `--model claude-fable-5`
- `.github/workflows/audit-deck.yml:77` — `--model claude-fable-5`
- `.github/workflows/refine-deck.yml:81` — `--model claude-fable-5`

## What changes

All three workflows hand the Claude Code CLI a model override through
`claude_args`:

```yaml
claude_args: |
  --max-turns 120
  --permission-mode bypassPermissions
  --model claude-fable-5
```

Each becomes `--model opus`. The alias resolves to the strongest
available Opus at run time — Claude Opus 5 as of this card's filing.

## Why the alias and not `claude-opus-5`

This repo has already litigated pinned-id-vs-alias twice, in opposite
directions, and both conclusions still hold in their own scope:

- [float-opus-alias-on-autonomous-github-workflows](../float-opus-alias-on-autonomous-github-workflows/)
  replaced the pinned `claude-opus-4-7` with `opus` because the pin
  went stale the moment Opus 4.8 shipped, leaving the autonomous
  runners implementing cards on a superseded model until a human
  edited YAML.
- [re-pin-autonomous-workflows-to-fable-5-after-re-enable](../re-pin-autonomous-workflows-to-fable-5-after-re-enable/)
  set an explicit `claude-fable-5`. That was not a reversal of the
  alias rationale — Fable is a *different tier*, not a newer Opus, so
  no Opus-tracking alias could express it.

Moving back to the Opus tier makes the alias expressible again, so the
staleness argument governs: `opus` is the correct spelling of "run on
the best Opus", and `claude-opus-5` would re-introduce exactly the
manual-edit debt the first card removed.

## Why it matters

The autonomous fleet is the repo's own dogfood loop: `pull-card`
implements and closes real deck cards, `audit-deck` files new defect
cards, and `refine-deck` mutates card frontmatter and bodies. Whatever
model those three run on is the model that writes a large share of
this repo's commits, so the choice is a standing capability decision,
not a per-run flag.

## Fix (applied)

Three one-line `claude_args` edits, one per workflow, plus a forward
pointer on the superseded predecessor card. No engine, template, or
plugin-mirror surface is touched — these workflow files are repo-local
CI and are not shipped by `goc install`.

Verification: `grep -rn -- "--model" .github/workflows/` returns
exactly three lines, all `--model opus`
(`pull-card.yml:101`, `audit-deck.yml:77`, `refine-deck.yml:81`); no
`claude-fable-5` override remains anywhere under `.github/workflows/`.
`claude.yml`, `claude-code-review.yml`, and the `release.yml` smoke
jobs keep the `claude-code-action` default and were left untouched, as
in every prior model-pin card.

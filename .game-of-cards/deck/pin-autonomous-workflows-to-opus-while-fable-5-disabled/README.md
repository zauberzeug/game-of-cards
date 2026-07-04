---
title: pin-autonomous-workflows-to-opus-while-fable-5-disabled
status: done
stage: null
contribution: low
created: "2026-06-15T04:02:15Z"
closed_at: "2026-06-15T04:04:34Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra]
summary: "Claude Fable 5 is disabled right now, so the two autonomous-agent workflows (audit-deck, pull-card) that pin `--model claude-fable-5` cannot run on it. Revert both `claude_args` model overrides to `--model opus` so the unattended audit and pull-queue runs keep working. Reverses agent-workflows-pin-opus-instead-of-latest-fable-5-model; re-pin fable-5 once it is re-enabled."
definition_of_done: |
  - [x] MECHANICAL: `.github/workflows/audit-deck.yml` passes `--model opus` in `claude_args`
  - [x] MECHANICAL: `.github/workflows/pull-card.yml` passes `--model opus` in `claude_args`
  - [x] MECHANICAL: `grep -rn -- "--model" .github/workflows/` shows no remaining `claude-fable-5` override
worker: {who: Rodja Trappe, where: main}
---

# pin-autonomous-workflows-to-opus-while-fable-5-disabled

> Later evidence: Claude Fable 5 was re-enabled; the re-pin recorded in
> this card's summary happened via
> [re-pin-autonomous-workflows-to-fable-5-after-re-enable](../re-pin-autonomous-workflows-to-fable-5-after-re-enable/)
> (2026-07-04). The `--model opus` state this card established is no
> longer current.

## Location

- `.github/workflows/audit-deck.yml:77` — `--model opus` (was `--model claude-fable-5`)
- `.github/workflows/pull-card.yml:104` — `--model opus` (was `--model claude-fable-5`)

## What's broken

Both autonomous-agent workflows hand the Claude Code CLI a model
override via `claude_args`:

```yaml
claude_args: |
  --max-turns 200
  --permission-mode bypassPermissions
  --model claude-fable-5
```

Claude Fable 5 (`claude-fable-5`) is disabled right now, so an
unattended run that requests it cannot start. These two workflows do
the repo's unattended work — filing audit cards and draining the
autonomous pull queue — so a disabled model pin silently stalls the
repo's self-maintenance.

The earlier card
[agent-workflows-pin-opus-instead-of-latest-fable-5-model](../agent-workflows-pin-opus-instead-of-latest-fable-5-model/)
made the opus→fable-5 switch on the (still correct) reasoning that
Fable 5 is the most capable model for long-horizon agentic work. That
reasoning is not wrong; Fable 5 is simply unavailable at the moment.
This card is the operational reversal, not a refutation.

This episode re-tests the principle set by
[float-opus-alias-on-autonomous-github-workflows](../float-opus-alias-on-autonomous-github-workflows/):
autonomous CI should pass a floating tier alias (`opus`), not a pinned
model ID. The fable-5 pin re-introduced the very availability fragility
that card resolved; floating back to `opus` is the resilient default.
The pin is only justified for a deliberate cross-tier jump (no `latest`
alias spans tiers), and must be reverted the moment that ID is disabled.

## Fix (applied)

Replaced `--model claude-fable-5` with `--model opus` in both
`claude_args` blocks. `opus` is the Claude Code alias for the current
Opus-tier model (Opus 4.8), which is available and is the strongest
model the autonomous runs can use while Fable 5 is disabled.

```
$ grep -rn -- "--model" .github/workflows/
.github/workflows/audit-deck.yml:77:            --model opus
.github/workflows/pull-card.yml:104:            --model opus
```

The other claude-code-action consumers in `.github/` (`claude.yml`,
`claude-code-review.yml`, the two smoke-test jobs in `release.yml`)
pass no `--model` flag and inherit the action's default; they are
left untouched.

## Why it matters

The audit-deck and pull-card workflows are the repo's autonomous
self-maintenance loop. A model override that points at a disabled
model is a silent stall — the runs request a model they cannot get
instead of doing work. Reverting to the available Opus alias keeps
the loop running.

## When Fable 5 is re-enabled

Re-pin both workflows to `--model claude-fable-5` (the change made by
[agent-workflows-pin-opus-instead-of-latest-fable-5-model](../agent-workflows-pin-opus-instead-of-latest-fable-5-model/))
and file a fresh card recording the flip back.

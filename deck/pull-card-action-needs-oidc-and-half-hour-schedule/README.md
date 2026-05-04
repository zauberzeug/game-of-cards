---
title: pull-card-action-needs-oidc-and-half-hour-schedule
summary: "The Pull Card GitHub Actions workflow is active, but scheduled runs fail before Claude can pull a card because the workflow does not grant the OIDC permission required by anthropics/claude-code-action@v1. The workflow should also run on a direct 30-minute cron instead of the earlier 10-minute wake-up plus configurable schedule gate."
status: active
stage: null
contribution: high
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] `pull-card.yml` grants `id-token: write` for the Claude action's OIDC token request
  - [ ] `pull-card.yml` uses a native 30-minute GitHub Actions cron
  - [ ] `uv run python deck/pull-card-action-needs-oidc-and-half-hour-schedule/reproduce.py` exits zero
  - [ ] `uv run goc validate --quiet` exits zero
---

# Pull Card action needs OIDC and a half-hour schedule

## Summary

The Pull Card workflow exists and GitHub reports it as active, but the scheduled
runs fail before `Skill(pull-card)` can execute. The Claude action tries to fetch
an OIDC token, while `.github/workflows/pull-card.yml` only grants
`contents`, `pull-requests`, and `issues` permissions.

The same workflow is currently configured around a 10-minute wake-up cadence and
a shell gate. The requested operational cadence is simpler: run the workflow
directly every 30 minutes.

## Location

`.github/workflows/pull-card.yml:13`

## What's broken

Remote evidence from `gh run view 25321913675 --log-failed`:

```text
Attempt 3 failed: Could not fetch an OIDC token. Did you remember to add `id-token: write` to your workflow permissions?
Action failed with error: Could not fetch an OIDC token.
```

Current workflow excerpt:

```yaml
on:
  schedule:
    - cron: '3/10 * * * *'

permissions:
  contents: write
  pull-requests: write
  issues: write
```

## Empirical evidence

Run before the fix:

```text
defect present: pull-card workflow is not ready to execute every 30 minutes
- permissions.id-token is not write
- schedule cron is ['3/10 * * * *'], expected ['*/30 * * * *']
- workflow still contains the old schedule gate
```

## Why it matters

The scheduled workflow reaches the Claude action and then fails immediately, so
the cloud runner never drains the deck. The cadence is also not the requested
30-minute interval.

## Fix

Change `.github/workflows/pull-card.yml` to:

- use a native `*/30 * * * *` schedule,
- remove the redundant schedule-gate step,
- grant `id-token: write` under workflow permissions.

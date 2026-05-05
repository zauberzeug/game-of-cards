---
title: schedule-pull-card-cloud
summary: "Add a configurable GitHub Actions cloud schedule that invokes the Claude Code pull-card skill."
status: done
stage: null
contribution: high
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [x] `.github/workflows/pull-card.yml` schedules cloud wake-up ticks for `pull-card`
  - [x] Scheduled cadence is configurable through `PULL_CARD_INTERVAL_MINUTES`
  - [x] Workflow can also be triggered manually
  - [x] Workflow prevents overlapping autonomous workers
  - [x] Scheduled prompt tells Claude to use `uv run goc ...` in this repo
---

# Schedule pull-card in cloud

## Summary

Run the GoC autonomous worker from GitHub Actions so the deck can make
progress without a local Claude Code session staying open. Keep the
actual cadence configurable from the GitHub repository settings rather
than hard-wiring a single interval in the prompt or workflow logic.

## Location

`.github/workflows/pull-card.yml`

## What's missing

The repo documents `/loop pull-card 30m` and scheduled `pull-card`
invocations in the shipped skill text, but it has no cloud runner that
actually invokes the skill on a recurring cadence.

## Fix

Add a GitHub Actions workflow that:

- wakes up on a 10-minute cron cadence,
- uses `PULL_CARD_INTERVAL_MINUTES` as the actual scheduled cadence,
- supports `workflow_dispatch` for manual runs,
- sets concurrency so scheduled ticks do not overlap,
- prepares `uv` before the agent starts,
- invokes `anthropics/claude-code-action@v1` with a prompt to run
  `Skill(pull-card)` once,
- grants only the Bash command families needed for this repo's GoC
  workflow and verification commands.

The workflow requires the repository secret `ANTHROPIC_API_KEY`.

The optional repository variable `PULL_CARD_INTERVAL_MINUTES` controls
the actual scheduled cadence. It defaults to `10` and must be at least
10 and a multiple of 10 because GitHub Actions cron is the wake-up
mechanism.

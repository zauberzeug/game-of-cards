---
title: schedule-pull-card-cloud
summary: "Add a GitHub Actions cloud schedule that invokes the Claude Code pull-card skill every 10 minutes."
status: active
stage: null
contribution: high
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [ ] `.github/workflows/pull-card.yml` schedules one `pull-card` run every 10 minutes
  - [ ] Workflow can also be triggered manually
  - [ ] Workflow prevents overlapping autonomous workers
  - [ ] Scheduled prompt tells Claude to use `uv run goc ...` in this repo
---

# Schedule pull-card in cloud

## Summary

Run the GoC autonomous worker from GitHub Actions so the deck can make
progress without a local Claude Code session staying open.

## Location

`.github/workflows/pull-card.yml`

## What's missing

The repo documents `/loop pull-card 30m` and scheduled `pull-card`
invocations in the shipped skill text, but it has no cloud runner that
actually invokes the skill on a recurring cadence.

## Fix

Add a GitHub Actions workflow that:

- runs on a 10-minute cron cadence,
- supports `workflow_dispatch` for manual runs,
- sets concurrency so scheduled ticks do not overlap,
- prepares `uv` before the agent starts,
- invokes `anthropics/claude-code-action@v1` with a prompt to run
  `Skill(pull-card)` once,
- grants only the Bash command families needed for this repo's GoC
  workflow and verification commands.

The workflow requires the repository secret `ANTHROPIC_API_KEY`.

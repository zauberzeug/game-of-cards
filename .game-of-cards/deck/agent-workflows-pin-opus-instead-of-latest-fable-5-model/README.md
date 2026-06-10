---
title: agent-workflows-pin-opus-instead-of-latest-fable-5-model
status: active
stage: null
contribution: low
created: "2026-06-10T07:43:15Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra]
summary: "The two autonomous-agent GitHub Actions workflows (audit-deck, pull-card) pass `--model opus` to claude-code-action, pinning the agent to the Opus alias. Anthropic's latest and most capable model is Claude Fable 5 (`claude-fable-5`); the workflows should run on it."
definition_of_done: |
  - [ ] MECHANICAL: `.github/workflows/audit-deck.yml` passes `--model claude-fable-5` in `claude_args`
  - [ ] MECHANICAL: `.github/workflows/pull-card.yml` passes `--model claude-fable-5` in `claude_args`
  - [ ] MECHANICAL: no other workflow passes a `--model` flag that still resolves to opus (`grep -rn 'model' .github/workflows/` audited)
worker: {who: Rodja Trappe, where: main}
---

# agent-workflows-pin-opus-instead-of-latest-fable-5-model

## Location

- `.github/workflows/audit-deck.yml:77` — `--model opus`
- `.github/workflows/pull-card.yml:104` — `--model opus`

## What's outdated

Both autonomous-agent workflows hand the Claude Code CLI a model override
via `claude_args`:

```yaml
claude_args: |
  --max-turns 200
  --permission-mode bypassPermissions
  --model opus
```

`opus` is the Claude Code alias for the current Opus-tier model
(Opus 4.8 as of this filing). Anthropic now ships Claude Fable 5
(`claude-fable-5`), a tier above Opus and the most capable model
available. These two workflows do the repo's unattended work —
filing audit cards and draining the autonomous pull queue — which is
exactly the long-horizon agentic workload the stronger model is built
for.

The other claude-code-action consumers in `.github/` (`claude.yml`,
`claude-code-review.yml`, the two smoke-test jobs in `release.yml`)
pass no `--model` flag and inherit the action's default; they are
intentionally left untouched.

## Fix

Replace `--model opus` with `--model claude-fable-5` in both
`claude_args` blocks. `claude-fable-5` is the exact model ID (no date
suffix); Claude Code's `--model` flag accepts full model IDs as well
as aliases.

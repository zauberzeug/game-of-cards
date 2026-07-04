---
title: re-pin-autonomous-workflows-to-fable-5-after-re-enable
status: done
stage: null
contribution: low
created: "2026-07-04T13:16:15Z"
closed_at: "2026-07-04T13:19:00Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra]
summary: "Claude Fable 5 is available again, so the autonomous-agent workflows (pull-card, audit-deck, refine-deck) should run on it instead of the `--model opus` fallback they were reverted to while it was disabled. Set all three `claude_args` model overrides back to `--model claude-fable-5`. Reverses pin-autonomous-workflows-to-opus-while-fable-5-disabled."
definition_of_done: |
  - [x] MECHANICAL: `.github/workflows/pull-card.yml` passes `--model claude-fable-5` in `claude_args`
  - [x] MECHANICAL: `.github/workflows/audit-deck.yml` passes `--model claude-fable-5` in `claude_args`
  - [x] MECHANICAL: `.github/workflows/refine-deck.yml` passes `--model claude-fable-5` in `claude_args`
  - [x] MECHANICAL: `grep -rn -- "--model" .github/workflows/` shows no remaining `opus` override
  - [x] PROCESS: closed predecessor card pin-autonomous-workflows-to-opus-while-fable-5-disabled amended with a forward pointer to this card
worker: {who: Rodja Trappe, where: main}
---

# re-pin-autonomous-workflows-to-fable-5-after-re-enable

## Location

- `.github/workflows/pull-card.yml:101` — `--model opus` (should be `--model claude-fable-5`)
- `.github/workflows/audit-deck.yml:77` — `--model opus` (should be `--model claude-fable-5`)
- `.github/workflows/refine-deck.yml:81` — `--model opus` (should be `--model claude-fable-5`)

## What's missing

All three autonomous-agent workflows hand the Claude Code CLI a model
override via `claude_args`:

```yaml
claude_args: |
  --max-turns 120
  --permission-mode bypassPermissions
  --model opus
```

The `opus` value is a deliberate fallback from
[pin-autonomous-workflows-to-opus-while-fable-5-disabled](../pin-autonomous-workflows-to-opus-while-fable-5-disabled/),
whose summary records the re-pin condition explicitly: "re-pin
fable-5 once it is re-enabled." Claude Fable 5 is available again,
and the maintainer has asked for the default model on the GitHub
workflows to go back to `claude-fable-5`.

`refine-deck.yml` did not exist during the original fable-5 pin
(it was created with `--model opus` in commit 870bce3), so it is
included here for the first time rather than reverted — the intent
is one consistent model override across the autonomous fleet.

## Why it matters

`claude-fable-5` is the top-tier model for long-horizon agentic
work (the rationale established by the closed card
[agent-workflows-pin-opus-instead-of-latest-fable-5-model](../agent-workflows-pin-opus-instead-of-latest-fable-5-model/)).
The unattended pull/audit/refine runs are exactly the long-horizon
sessions that benefit; leaving them on the fallback model after the
outage ended silently under-serves the autonomous loop.

## Fix

Change `--model opus` to `--model claude-fable-5` in the
`claude_args` block of each of the three workflow files listed
above. The other claude-code-action consumers (`claude.yml`,
`claude-code-review.yml`, `release.yml` smoke jobs) intentionally
keep the action default and are out of scope, as before.

---
title: unblock-scheduled-pull-card-secret
summary: Unblock the scheduled pull-card GitHub Action by providing a repository-level model API secret and verifying the workflow reaches the agent step.
status: done
stage: null
contribution: high
created: 2026-05-05
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [x] Repository secret `ANTHROPIC_API_KEY` is set for `zauberzeug/game-of-cards`, or the workflow is intentionally switched to another provider with the matching secret.
  - [x] `.github/workflows/pull-card.yml` documents or clearly references the required secret name.
  - [x] A manual `pull-card` workflow run reaches the agent execution step without failing on missing credentials.
  - [x] The verification run URL is recorded in this card's log.
---

# Unblock scheduled pull-card secret

## Summary

The cloud `pull-card` workflow is installed, but the latest manual test run failed before Claude could execute because GitHub Actions could not find model credentials:

```text
Either ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN is required
```

`gh secret list --repo zauberzeug/game-of-cards` showed no repository secrets at the time of debugging.

## Why it matters

Without the model API secret, the scheduled GoC worker cannot make autonomous progress from GitHub Actions. The workflow itself is present, but every scheduled or manual run will stop at credential setup.

## Human gate

The actual secret value must not be stored in the repo or Slack. A human with access to the key needs to set it through GitHub Actions secrets, for example:

```bash
gh secret set ANTHROPIC_API_KEY --repo zauberzeug/game-of-cards
```

If the repo should use Codex instead of Claude, update the workflow intentionally and set the corresponding provider secret, e.g. `OPENAI_API_KEY`, rather than leaving the current Claude workflow half-configured.

## Verification

After the secret is set, trigger the workflow manually and record the run URL in `log.md`.

## Decision

*Resolved 2026-05-05:* Switch pull-card.yml to CLAUDE_CODE_OAUTH_TOKEN provisioned by the Claude GitHub App

*Reasoning:* PR #1 installed the Claude GitHub App, which provisions CLAUDE_CODE_OAUTH_TOKEN automatically; ANTHROPIC_API_KEY was never set, so this is the lower-friction path the DoD explicitly allows ('intentionally switched to another provider with the matching secret')

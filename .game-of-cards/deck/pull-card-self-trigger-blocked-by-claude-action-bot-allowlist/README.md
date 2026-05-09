---
title: pull-card-self-trigger-blocked-by-claude-action-bot-allowlist
summary: "Empirical verification (`pull-card-self-trigger-needs-empirical-verification`, done 2026-05-09) confirmed that `pull-card.yml`'s `gh workflow run` self-trigger step succeeds — a new `workflow_dispatch` run is created — but the resulting iteration N+1 run fails immediately on `claude-code-action@v1`'s bot-actor allowlist check (`Workflow initiated by non-human actor: github-actions (type: Bot). Add bot to allowed_bots list or use '*' to allow all bots.`). The chain is therefore non-functional in practice; only `event: schedule` runs drain the queue. Decide between (a) adding `allowed_bots: github-actions[bot]` to the workflow's action inputs, (b) dropping the self-trigger and tightening cron, or (c) using a different trigger mechanism. The earlier resolution (`No PAT, no GitHub App`) constrains the option set."
status: open
stage: null
contribution: medium
created: 2026-05-09
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - pull-card-self-trigger-needs-empirical-verification
tags: [bug, infra]
definition_of_done: |
  - [ ] Decision recorded: `allowed_bots: github-actions[bot]`, cron-only with tighter cadence, or another mechanism
  - [ ] If `allowed_bots`: workflow updated; one iteration=N+1 run observed completing successfully (agent step runs, drains a card)
  - [ ] If cron-only: self-trigger steps removed from `pull-card.yml`; cron schedule tightened (e.g., `*/10 * * * *` or `*/15`); MAX_ITERATIONS env var dropped
  - [ ] Parent card (`self-trigger-pull-card-workflow-for-fresh-context-per-card`) updated with the decision and final state
  - [ ] `uv run goc validate` passes
---

# Pull-card self-trigger blocked by claude-code-action bot allowlist

## What's verified

`pull-card-self-trigger-needs-empirical-verification` (closed 2026-05-09) ran the verification. Findings:

- The `gh workflow run pull-card.yml -f iteration=<n+1>` step succeeds with the default `GITHUB_TOKEN` and `permissions.actions: write`. No 403. A new run with `event: workflow_dispatch` is created and visible in the run list. (Empirical: runs `25598906055` and `25597987648` both started cleanly; both were triggered by `github-actions[bot]`.)
- The iteration=N+1 run then fails at the `Pull one card` step with:

  ```
  Action failed with error: Workflow initiated by non-human actor: github-actions (type: Bot).
  Add bot to allowed_bots list or use '*' to allow all bots.
  ```

  This check lives in `anthropics/claude-code-action@v1`'s `action.yml`: an `allowed_bots` input that defaults to empty (no bots permitted).

- Net effect: only `event: schedule` (cron) iterations actually drain cards. Self-triggered iterations create runs that die before the agent step. The parent card's "fresh-context-per-card" benefit is realized for cron-tick boundaries only.

## Three options

### Option (a) — `allowed_bots: github-actions[bot]`

Add this line to the action's `with:` block in `pull-card.yml`:

```yaml
- name: Pull one card
  uses: anthropics/claude-code-action@v1
  with:
    allowed_bots: github-actions[bot]
    ...
```

This is the action's own first-class knob. Restricting to `github-actions[bot]` (not `*`) means only the same-repo `GITHUB_TOKEN`-as-actor can trigger it; external Apps would still be rejected. The action's `claude_args: --permission-mode bypassPermissions` is already trusting the workflow's prompt regardless of trigger origin, so the marginal security delta is small: any actor that can dispatch this workflow already controls the prompt's effects.

Risk: action upstream may treat `github-actions[bot]` and other bots equivalently in future versions. Mitigation: pin a specific version tag (already pinned to `v1`).

### Option (b) — cron-only with tighter cadence

Remove the self-trigger step (and `MAX_ITERATIONS`, and `permissions.actions: write`) from `pull-card.yml`. Tighten cron from `0 * * * *` (hourly) to `*/15 * * * *` or `*/10 * * * *` so queue drain rate stays acceptable.

This is what was pre-approved in `pull-card-self-trigger-needs-empirical-verification`'s decision body: *"If the chain fails ... fall back to cron-only with a tighter schedule. No PAT, no GitHub App."* The empirical finding fits the spirit of "chain fails" (chain doesn't drain queue end-to-end) even though the failure mode differs from the originally-anticipated 403.

Cost: every iteration starts cold (no prompt-cache reuse across iterations within a queue-drain burst). At MAX_ITERATIONS=8 the current self-trigger design would have completed an 8-card drain in ~30-60 minutes; cron-every-15-minutes completes the same drain in 2 hours. Acceptable for low-urgency autonomous work.

### Option (c) — different mechanism

PAT or GitHub App with workflow scope, or `repository_dispatch`. Pre-rejected by the parent decision (`No PAT, no GitHub App`). Listed for completeness only.

## Recommendation

Option (a) is the lowest-cost path that preserves the parent card's design intent. It's a one-line YAML change with bounded security delta (specific bot, not `*`). If Rodja prefers to honor the original "no new permissions/credentials" posture strictly, option (b) is the clean cron-only fallback.

## Decision required

Pick (a), (b), or another path. Then a pull-card session can implement it directly.

## Cross-references

- `pull-card-self-trigger-needs-empirical-verification` (done 2026-05-09) — the empirical finding feeding this card
- `self-trigger-pull-card-workflow-for-fresh-context-per-card` (done 2026-05-09) — the original design that this card amends
- `drain-pull-card-queue-per-cron-tick` (done) — the predecessor design and natural fallback for option (b)

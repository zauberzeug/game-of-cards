---
title: pull-card-self-trigger-needs-empirical-verification
summary: "`self-trigger-pull-card-workflow-for-fresh-context-per-card` (closed 2026-05-09) restructured `pull-card.yml` so each iteration is its own GitHub Actions run, chained via `gh workflow run` self-trigger using the default `GITHUB_TOKEN` and `permissions.actions: write`. The closed card cites GitHub docs that exempt `workflow_dispatch` from the no-cascade rule. A 2026-05-09 review flagged this as likely-broken because a sibling commit (`6794c03`, 'app lacks workflows permission') reverted a different change for the same-named permission. The two are not the same — `6794c03` failed because the bot tried to MUTATE `.github/workflows/*.yml` content; this design only DISPATCHES via `gh workflow run`. The empirical question is whether the chain actually self-triggers on a real cron tick. Verify before any redesign."
status: open
stage: null
contribution: high
created: 2026-05-09
closed_at: null
human_gate: none
advances: []
advanced_by:
  - self-trigger-pull-card-workflow-for-fresh-context-per-card
tags: [bug, infra]
definition_of_done: |
  - [ ] Trigger `pull-card.yml` manually (workflow_dispatch with `iteration=1`) against a queue of at least 2 `human_gate: none` open cards
  - [ ] Observe whether the `gh workflow run` self-trigger step succeeds and the `iteration=2` run starts; capture run URL or full log excerpt in this card's body
  - [ ] If the chain works: append a "Verified" note to `self-trigger-pull-card-workflow-for-fresh-context-per-card`'s README and close this card
  - [ ] If `gh workflow run` returns 403 / lacks permission: file a follow-up redesign card (PAT secret, GitHub App with `workflows` scope, or pure-cron alternative), link it via `advances`, and close this card
  - [ ] Decision recorded either way so the next reader doesn't re-litigate the question
---

# Pull-card self-trigger needs empirical verification

## What's claimed vs. what's been observed

`self-trigger-pull-card-workflow-for-fresh-context-per-card` (closed
2026-05-09) ships a `pull-card.yml` that calls `gh workflow run
pull-card.yml -f iteration=<n+1>` from inside the workflow itself, using
`${{ github.token }}` with `permissions.actions: write`. The card cites
[GitHub docs](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow)
that exempt `workflow_dispatch` and `repository_dispatch` from the
no-cascading-triggers rule for the default `GITHUB_TOKEN`. The DoD
checkbox `permissions.actions: write added so the default GITHUB_TOKEN
can dispatch the next run` is checked, but does not record an
empirical confirmation that the chain actually fires.

## Why this is contested

A 2026-05-09 review flagged the design as broken on the grounds that
the Actions API endpoint for workflow dispatch requires the token to
have `workflows` permission, which `actions: write` does not grant.
The review cited commit `6794c03` ("app lacks workflows permission")
as evidence the team already hit this wall.

`6794c03`'s actual context is different. It reverted a workflow YAML
*content* change because the bot's GitHub App lacked the `workflows`
scope required to PUSH commits that mutate files under
`.github/workflows/`. That is a content-mutation permission, not a
runtime-dispatch permission. The two are conflated in the revert
message but are governed by different rules.

So the design might work as documented, or might fail with a 403 on
the first self-trigger. Without an empirical run, we cannot tell.

## What needs to happen

1. Trigger `pull-card.yml` via `workflow_dispatch` with at least two
   `human_gate: none` open cards in the queue.
2. Watch the run. Two outcomes:
   - **Chain succeeds:** `iteration=2` starts within ~30s of
     `iteration=1` finishing, and we see a fresh-context run pull
     the next card. Verified — close this card and append a
     "Verified live in run <URL>" line to the parent card's README.
   - **Chain fails:** the `gh workflow run` step returns 403 with
     "Resource not accessible by integration" or similar permission
     error. The chain stops. Cards remain stranded until next cron
     tick. File a redesign card with the three plausible mitigations
     (PAT secret, GitHub App with `workflows` scope, or remove
     self-trigger and rely on tighter cron).

## Decision

*Resolved 2026-05-09:* Run the verification by triggering pull-card.yml via workflow_dispatch with iteration=1; observe whether the self-trigger chain fires iteration=2 successfully. If the chain fails (gh workflow run returns 403 or similar), fall back to cron-only with a tighter schedule (e.g., */10 minutes) and one card per tick. No PAT, no GitHub App.

*Reasoning:* Cron-only with tighter schedule preserves fresh-context-per-card (the architectural goal of the parent card) without new secrets or permission changes. Aligns with the drop-third-party-runtime-dependencies-from-goc epic energy and keeps the autonomous loop simple. Slower drain is acceptable for low-urgency work; queue can be tightened further if it grows faster than drain.
## Cross-references

- `self-trigger-pull-card-workflow-for-fresh-context-per-card` (done) —
  the design under verification
- `drain-pull-card-queue-per-cron-tick` (done) — the predecessor
  design, which would be the natural fallback if self-trigger doesn't
  work
- `pin-opus-on-autonomous-github-workflows` (done) — sibling that
  pinned the model used in pull-card runs

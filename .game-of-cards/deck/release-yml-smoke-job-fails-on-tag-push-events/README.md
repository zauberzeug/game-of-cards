---
title: release-yml-smoke-job-fails-on-tag-push-events
summary: "The smoke job in `.github/workflows/release.yml` uses `anthropics/claude-code-action@v1`, which rejects `push` event types with `Action failed with error: Unsupported event type: push`. On a tag push (the documented release trigger), build runs, smoke errors, and publish is silently skipped because of `needs: [build, smoke]`. A human watching the Actions tab sees a red smoke job and has to know the workaround: re-trigger via `gh workflow run release.yml --ref vX.Y.Z` so the dispatch event fires the supported workflow_dispatch path through the action while github.ref still resolves to refs/tags/v… so publish's tag-ref guard fires."
status: active
stage: null
contribution: medium
created: 2026-05-09
closed_at: null
human_gate: none
advances: []
advanced_by:
  - cut-v0-0-7-release-before-openclaw-publish
tags: [bug, infra]
definition_of_done: |
  - [ ] Reproduce: verify the failure mode by inspecting CI run `25608246745` (the v0.0.7 tag-push attempt) — build OK, smoke errored on `Unsupported event type: push`, publish skipped
  - [ ] Decide on a fix shape (skip-smoke-on-push / split-smoke-into-separate-workflow / replace-action / inline-script-replacement) and record the choice in this card's body
  - [ ] Implement the chosen fix and verify by tag-pushing a throw-away pre-release tag (e.g., `v0.0.7-test`) — build, smoke, and publish all run end-to-end without manual workflow_dispatch follow-up
  - [ ] Delete the throw-away tag from origin
  - [ ] `release.yml` comment header updated to reflect the new release flow
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `release.yml` smoke job fails on tag push events

## Why

Discovered during the v0.0.7 release cut (`cut-v0-0-7-release-before-openclaw-publish`). The intended release flow is "push tag `vX.Y.Z` → CI verifies version match → CI builds wheel + sdist → CI runs smoke → CI publishes to PyPI via OIDC trusted publishing." On v0.0.7's tag push (run [25608246745](https://github.com/zauberzeug/game-of-cards/actions/runs/25608246745)) this fell over:

- ✓ Build (8s)
- ✗ Smoke — `Path A — kickoff completes against fresh repo`: `Action failed with error: Unsupported event type: push`
- — Publish: skipped (needs:smoke failed)

The action is `anthropics/claude-code-action@v1`. Per its source, it accepts `pull_request`, `pull_request_review`, `pull_request_review_comment`, `issues`, `issue_comment`, `workflow_dispatch`, and `repository_dispatch` — but not `push`. The smoke job's `if` allows it to run on tag pushes (`startsWith(github.ref, 'refs/tags/v')`), but the action itself doesn't handle that event family.

The workaround that successfully published v0.0.7 was `gh workflow run release.yml --ref v0.0.7` (run [25608296877](https://github.com/zauberzeug/game-of-cards/actions/runs/25608296877)) — workflow_dispatch is supported by the action, and `github.ref` still resolves to `refs/tags/v0.0.7` so publish's tag-ref guard still fires. But this is an undocumented procedural step. Future releases need either documentation of this two-step flow or, preferably, a workflow that just works on tag push.

## Why this only surfaced now

v0.0.6 was released via workflow_dispatch on `main` (run `25570760155`), apparently never via tag push. The smoke job was added in `2e393cd feat: release-time smoke test gates PyPI publish on plugin auto-bootstrap`, after which v0.0.6 was published via dispatch. v0.0.7 was the first tag-push-triggered release after the smoke job landed, so this is the first time the action-event-type mismatch had a chance to bite.

## Fix shapes worth considering

1. **Skip smoke on push events**: change `smoke.if` to `${{ github.event_name == 'workflow_dispatch' }}` and remove `smoke` from `publish.needs`. Tag push goes build → publish. Smoke is exercised separately via workflow_dispatch dry-runs. Lose: smoke gating on real tag-push releases. Gain: tag push works as documented.
2. **Split smoke into a separate workflow**: a `smoke.yml` runs on workflow_dispatch only and is treated as a manual pre-release check. `release.yml` keeps its build → publish chain on tag push. Same gain/loss profile as (1) but separates concerns.
3. **Replace the action**: drop `anthropics/claude-code-action@v1` for an inline script that exercises the smoke paths without depending on a third-party event-type-restricted action. More work but removes the constraint entirely.
4. **Trigger smoke as a `workflow_run` consequence** of the build job, dispatched programmatically. Adds complexity; not recommended.

(1) is the smallest viable fix. (3) is the "right" answer if smoke gating on every release is non-negotiable.

## Reproduction pointer

CI run `25608246745` (failed tag-push attempt). The error string `Unsupported event type: push` is the smoking gun.

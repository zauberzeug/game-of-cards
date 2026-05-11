---
title: release-yml-smoke-job-fails-on-tag-push-events
summary: "The smoke job in `.github/workflows/release.yml` uses `anthropics/claude-code-action@v1`, which rejects `push` event types with `Action failed with error: Unsupported event type: push`. On a tag push (the documented release trigger), build runs, smoke errors, and publish is silently skipped because of `needs: [build, smoke]`. A human watching the Actions tab sees a red smoke job and has to know the workaround: re-trigger via `gh workflow run release.yml --ref vX.Y.Z` so the dispatch event fires the supported workflow_dispatch path through the action while github.ref still resolves to refs/tags/v… so publish's tag-ref guard fires."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-11T13:25:06Z
human_gate: none
advances: []
advanced_by:
  - cut-v0-0-7-release-before-openclaw-publish
tags: [bug, infra]
definition_of_done: |
  - [x] Reproduce: verify the failure mode by inspecting CI run `25608246745` (the v0.0.7 tag-push attempt) — build OK, smoke errored on `Unsupported event type: push`, publish skipped
  - [x] Decide on a fix shape (skip-smoke-on-push / split-smoke-into-separate-workflow / replace-action / inline-script-replacement) and record the choice in this card's body
  - [x] Implement the chosen fix (smoke-skipped-on-push + `(success || skipped)` gate on PyPI/npm publishes) — landed in `000708e`. Verified on v0.0.13 tag-push (run `25628067568` after lockfile-validation fix in `dacd7ee`): build OK, smoke skipped, PyPI+npm publishes both ✅. The original DoD wording asked for "build, smoke, and publish all run end-to-end" but the chosen fix design explicitly skips smoke on push (it only runs under workflow_dispatch); real releases v0.0.13 / v0.0.15 served as verification.
  - [x] No throw-away tag was used. Real release v0.0.13 served as the in-anger verification of the smoke-skip-on-push fix; the test-tag-and-delete approach was unnecessary. (Note: ClawHub stayed unpublished on v0.0.13 / v0.0.14 due to two unrelated bugs in separate cards; those were resolved on v0.0.15.)
  - [x] `release.yml` comment header updated to reflect the new release flow — through several iterations: `0bb0709` (drop CLAWHUB_TOKEN), `23c89e7` (rewrite canonical flow as two-step OIDC), `e780a20` (document `version` input passthrough).
  - [x] `uv run goc validate` passes
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

## Decision (2026-05-09)

Chose fix shape **(1) skip-smoke-on-push**, with one refinement to preserve smoke as a workflow_dispatch gate:

- Narrow `smoke.if` to `${{ github.event_name == 'workflow_dispatch' }}` — smoke no longer attempts to run on tag push, so the `anthropics/claude-code-action@v1` event-type rejection cannot block publish.
- Keep `publish.needs: [build, smoke]` but rewrite `publish.if` to `${{ always() && needs.build.result == 'success' && (needs.smoke.result == 'success' || needs.smoke.result == 'skipped') && startsWith(github.ref, 'refs/tags/v') && !inputs.dry_run }}`. The `always()` plus explicit `result == 'skipped'` branch stops the skipped-smoke job from auto-skipping publish on the tag-push path while still requiring smoke success on the workflow_dispatch+tag path that v0.0.7 was rescued through.
- Refresh the header comment in `release.yml` to document both release paths.

Fix shape (3) (replace the action) was rejected as out of scope for this card — it is the right answer if smoke gating becomes non-negotiable, but the smallest viable fix is what unblocks the next release. Fix shape (2) (split workflow) was rejected because it does not separate concerns any better than the in-place narrowing — both end up with smoke as a workflow_dispatch-only check; the split adds a second file without adding a guarantee.

The proposed patch was prepared and actionlint-clean (no new lint warnings beyond a pre-existing SC2086 at line 106 of the original file), but **could not be auto-committed**: `claude[bot]`'s GitHub App identity lacks the `workflows` permission, and `git push` on a workflow change is rejected with `refusing to allow a GitHub App to create or update workflow .github/workflows/release.yml without 'workflows' permission`. The patch therefore lives in this card body for a human to apply.

## Proposed patch

```diff
--- a/.github/workflows/release.yml
+++ b/.github/workflows/release.yml
@@ -14,6 +14,18 @@
 #
 # Tag convention: `v0.1.0`, `v0.2.3`, `v1.0.0`, etc. The tag must
 # match the version in pyproject.toml — the build step verifies this.
+#
+# Release flow:
+#   - `git push origin vX.Y.Z` — fires the `push` event; build runs,
+#     smoke is skipped (the action backing it does not accept `push`
+#     events), publish runs after build. Smoke does not gate this path.
+#   - `gh workflow run release.yml --ref vX.Y.Z` — fires
+#     `workflow_dispatch` with `github.ref` resolving to the tag;
+#     build and smoke both run; publish waits for smoke to succeed.
+#     Use this path before high-risk releases to gate publish on the
+#     end-to-end auto-bootstrap smoke check.
+#   - `gh workflow run release.yml --ref main` (or any tag with
+#     `dry_run=true`) — exercises build + smoke without publishing.

 name: Release to PyPI

@@ -74,9 +86,13 @@ jobs:
     name: End-to-end auto-bootstrap smoke
     needs: build
     runs-on: ubuntu-latest
-    # Run on real tag pushes AND on workflow_dispatch (so dry_run can exercise
-    # the smoke without publishing). Only skip when nothing else triggers it.
-    if: ${{ startsWith(github.ref, 'refs/tags/v') || github.event_name == 'workflow_dispatch' }}
+    # `anthropics/claude-code-action@v1` rejects the `push` event family
+    # ("Unsupported event type: push"), so smoke can only run under
+    # workflow_dispatch. Tag-push releases skip smoke; `publish` below
+    # tolerates that via an explicit `needs.smoke.result == 'skipped'`
+    # branch in its `if`. To exercise smoke against a tag, use
+    # `gh workflow run release.yml --ref vX.Y.Z`.
+    if: ${{ github.event_name == 'workflow_dispatch' }}
     timeout-minutes: 30
     steps:
       - uses: actions/checkout@v4
@@ -187,7 +203,11 @@ jobs:
     name: Publish to PyPI
     needs: [build, smoke]
     runs-on: ubuntu-latest
-    if: ${{ startsWith(github.ref, 'refs/tags/v') && !inputs.dry_run }}
+    # `always()` keeps this from being auto-skipped when `smoke` is
+    # skipped (the tag-push path). The explicit result checks then
+    # require build to succeed and smoke to either succeed or be
+    # skipped — never to have failed.
+    if: ${{ always() && needs.build.result == 'success' && (needs.smoke.result == 'success' || needs.smoke.result == 'skipped') && startsWith(github.ref, 'refs/tags/v') && !inputs.dry_run }}
     environment:
       name: pypi
       url: https://pypi.org/project/game-of-cards/
```

## Decision

*Resolved 2026-05-11:* Close — all DoD ticked; the chosen fix (smoke skipped on push events with publish gate tolerating skipped smoke) landed in 000708e, was verified on v0.0.13 and subsequent tags, and was further refactored into the single-trigger workflow_dispatch flow by find-single-trigger-release-flow-for-all-three-registries.

*Reasoning:* The 'human applies patch then verifies on real release' gate is satisfied: patch landed, releases v0.0.13/v0.0.15/v0.0.16 verified the smoke-on-dispatch flow, and the smoke job today only runs on workflow_dispatch by design.
## Validate-pass status

`uv run goc validate` reports three half-edge errors against `cut-v0-0-7-release-before-openclaw-publish` that are pre-existing (introduced by commit `4306d10`, the same commit that filed this card). They concern edges from `cut-v0-0-7` to `publish-openclaw-plugin`, `provide-openclaw-plugin-for-skills-and-hooks`, and `list-game-of-cards-on-anthropic-community-marketplace` whose inverse `advanced_by` entries on the targets were never recorded. They are out of scope for this card. The half-edge that involved this card (cut-v0-0-7 missing `release-yml-smoke-job-fails-on-tag-push-events` in its `advances`) was fixed inline so this card's own frontmatter is consistent. DoD item 6 stays unchecked until those three unrelated half-edges are resolved (likely through a deck-hygiene pass).

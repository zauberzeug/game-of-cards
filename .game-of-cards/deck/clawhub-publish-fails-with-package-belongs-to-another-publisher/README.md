---
title: clawhub-publish-fails-with-package-belongs-to-another-publisher
summary: "On the v0.0.13 release run (workflow_dispatch, 2026-05-10), the `publish-clawhub / publish` job failed with `Uncaught ConvexError: Package already exists and belongs to another publisher`. PyPI (0.0.13) and npm (0.0.13) published cleanly in the same run, so the failure is ClawHub-specific. Hypothesis: the same-day npm-org rebrand (closed card `publish-npm-package-under-zauberzeug-org-not-personal`) re-anchored the publisher identity that the ClawHub trusted-publisher entry resolves to, and ClawHub's Convex store still tracks the existing `game-of-cards` package against the previous publisher — so the new identity hits the registry's ownership guard. Until this is resolved every tag push lands two-thirds of a release."
status: active
stage: null
contribution: high
created: 2026-05-10
closed_at: null
human_gate: none
advances:
  - publish-openclaw-plugin
  - provide-openclaw-plugin-for-skills-and-hooks
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] Reproduce the publisher mismatch locally with `clawhub package publish ./openclaw-plugin --version v0.0.13-test --dry-run` (or equivalent) and confirm whether the failure originates client-side (CLI) or server-side (Convex registry)
  - [ ] Identify the publisher identity ClawHub records for the existing `game-of-cards` package (CLI: `clawhub package show game-of-cards --json` or web UI) and the publisher identity the failing run presented (from the trusted-publisher entry / job identity)
  - [ ] Document the ownership-transfer or identity-realign path that ClawHub supports (CLI-driven, web UI, or support contact) and pick the one that requires the least manual intervention on future releases
  - [ ] Apply the fix: either transfer ownership in the ClawHub registry, re-register the trusted-publisher with the corrected identity, or rotate `CLAWHUB_TOKEN` to a token issued under the current owning account
  - [ ] Re-run the v0.0.13 ClawHub publish job (`gh workflow run release.yml --ref v0.0.13` or targeted job re-run) and confirm `clawhub package show game-of-cards --json` reports `0.0.13` as the latest version
  - [ ] Update CLAUDE.md release-flow guidance with the recovery procedure so the next maintainer who hits this knows the recipe
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# clawhub-publish-fails-with-package-belongs-to-another-publisher

## Evidence

- Run: <https://github.com/zauberzeug/game-of-cards/actions/runs/25629654305>
- Job: `publish-clawhub / publish` (id `75231120722`), step `Run package publish`
- Error line:
  `Error: Uncaught ConvexError: Uncaught ConvexError: Package already exists and belongs to another publisher`
- Same run: PyPI publish ✅ (`game-of-cards` 0.0.13 live), npm publish ✅ (`game-of-cards` 0.0.13 live, dist-tag `latest`)
- Trigger: `workflow_dispatch --ref v0.0.13` (per the recorded recovery recipe). Earlier `push`-event runs on the same tag failed for the unrelated smoke-job event-type bug; the workflow_dispatch retries reach the publish stage cleanly until ClawHub.

## Most likely cause

ClawHub's Convex registry records, per package, the publisher identity that originally registered it. The `game-of-cards` package was first registered under the maintainer's personal account during the v0.0.7-era manual `clawhub login` flow. On 2026-05-10 the npm package ownership was moved from a personal account to the Zauberzeug org (closed card `publish-npm-package-under-zauberzeug-org-not-personal`). The ClawHub trusted-publisher entry — last set with `clawhub package trusted-publisher set game-of-cards --repository zauberzeug/game-of-cards --workflow-filename release.yml` — resolves OIDC subjects through that GitHub repository, which now corresponds to a different owning account than the one Convex has on file for the package. Hence the registry rejects the publish at the ownership-guard layer: the *workflow* is authorized, but the *publisher record* on the package itself is not.

## Anti-evidence (things this is NOT)

- Not a token problem: the failure happens after authentication (the step "Write ClawHub config" succeeded; the failing step is `Run package publish`).
- Not the smoke-job-on-push bug (`release-yml-smoke-job-fails-on-tag-push-events`): this run was workflow_dispatch and the smoke job was green.
- Not a duplicate publish attempt: 0.0.13 has no prior ClawHub release; `npm view game-of-cards version` returns 0.0.13 but ClawHub's registry has no 0.0.13 record yet.
- Not a CLI-version drift: the `Resolve ClawHub workflow source` and `Install ClawHub CLI dependencies` steps both succeeded; the rejection is server-side.

## Out of scope

- Releasing v0.0.14. The `automate-version-bumping-from-git-tag-at-release-time` and `support-external-game-of-cards-state-location` work all landed in v0.0.13; nothing post-v0.0.13 is shippable yet. This card unblocks v0.0.13's ClawHub leg, not a new release.
- The smoke-job-on-push event-type bug (separate active card `release-yml-smoke-job-fails-on-tag-push-events`).
- The OpenClaw subagent `alsoAllow` projection bug (separate blocked card `openclaw-subagent-plugin-tools-alsoallow-ignored`).

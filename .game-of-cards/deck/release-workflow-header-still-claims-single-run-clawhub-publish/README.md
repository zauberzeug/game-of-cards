---
title: release-workflow-header-still-claims-single-run-clawhub-publish
summary: "The header comment of .github/workflows/release.yml still asserts the pre-v0.0.25 model — that a single from-main workflow_dispatch run publishes all three registries and that ClawHub's validator has \"no ref-pattern constraint\" — while the same file's job-level comments and the `redispatch-clawhub` job implement the opposite (ClawHub requires published commit == OIDC `sha`, so it publishes via an auto-dispatched second run on the tag ref). AGENTS.md sends readers to this stale header as the trusted-publisher reference. Fix is a mechanical header rewrite, but workflow-file edits cannot be pushed by the autonomous bot's GITHUB_TOKEN — needs a human-credentialed session."
status: open
stage: null
contribution: medium
created: "2026-07-16T01:02:08Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [ ] MECHANICAL: header lines claiming "all three publishes happen in the same run" / "all in the same workflow_dispatch run" / "Why single-event works for ClawHub … no ref-pattern constraint" are rewritten to the redispatch model already described at the `redispatch-clawhub` job
  - [ ] MECHANICAL: rewritten header agrees with AGENTS.md's release section (source-commit guard, auto re-dispatch on the tag ref, recovery commands)
  - [ ] EMPIRICAL: `grep -n "same run" .github/workflows/release.yml` no longer matches a ClawHub claim in the header
  - [ ] PROCESS: pushed by a human-credentialed session (bot GITHUB_TOKEN cannot modify .github/workflows/)
---

# release.yml header still claims single-run ClawHub publish

## Location

`.github/workflows/release.yml` header comment — the ClawHub
trusted-publisher paragraph (~lines 23-26), the flow summary
(~line 49), and the "Why single-event works for ClawHub" block
(~lines 61-68) — versus the job-level comments at ~lines 694-700 and
the `redispatch-clawhub` job at ~line 729.

## What's broken

The header asserts the superseded pre-v0.0.25 model:

> ClawHub's OIDC TP refuses `push` events and accepts only
> `workflow_dispatch`. Under the single-trigger canonical flow
> (see below), the workflow is entered only via workflow_dispatch,
> so all three publishes happen in the same run.

> publish-pypi, publish-npm, publish-clawhub: all OIDC trusted
> publishing, all in the same workflow_dispatch run.

> Why single-event works for ClawHub: the ClawHub reusable workflow's
> validator only checks `github.event_name == 'workflow_dispatch'` —
> there is no ref-pattern constraint, so a dispatch from
> `refs/heads/main` (with the tag created mid-run) passes …

The same file's job comments say the opposite (and match reality):

> equal the OIDC-verified `sha`. In a from-`main` `release` run the
> OIDC `sha` is the pre-rewrite dispatch HEAD, but we publish the
> bot's post-rewrite tag commit — they never match. So the `release`
> run delegates ClawHub to `redispatch-clawhub`, which re-dispatches
> this workflow on the tag ref …

AGENTS.md documents the corrected redispatch flow and then routes
readers straight into the stale text: "See
`.github/workflows/release.yml` header comment for trusted publisher
configuration details."

## Why it matters

The closed card
[clawhub-publish-fails-on-every-release-until-manual-tag-redispatch](../clawhub-publish-fails-on-every-release-until-manual-tag-redispatch/)
fixed the mechanism and the job comments but left the header — the
designated reference — asserting the disproved model, including the
specific claim ("no ref-pattern constraint … passes the same
validator") whose failure motivated the fix. A maintainer debugging a
release failure from the header will conclude a from-main dispatch
should have published ClawHub and mis-diagnose the guard rejection.

## Fix

Rewrite the header's ClawHub paragraphs to the redispatch model (the
correct prose already exists at the `redispatch-clawhub` job and in
AGENTS.md — this is consolidation, not new research). Parked at
`human_gate: session` only because the autonomous bot's
`GITHUB_TOKEN` cannot push edits under `.github/workflows/`; the
edit itself is mechanical.

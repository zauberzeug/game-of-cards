---
title: clawhub-package-publishes-pre-rewrite-package-json
status: done
stage: null
contribution: high
created: "2026-06-08T03:48:58Z"
closed_at: "2026-06-08T04:12:51Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] MECHANICAL: ClawHub publish job passes the post-rewrite release ref to the reusable workflow
  - [x] PROCESS: Release-workflow comments explain why `version:` alone is insufficient
  - [x] TDD: Regression coverage catches a ClawHub job wired only to metadata override
  - [x] EMPIRICAL: Verification confirms PyPI/npm/tag are already version-correct while ClawHub payload source was stale
worker: {who: Rodja Trappe, where: main}
---

# ClawHub package publishes pre-rewrite package.json

## Summary

The v0.0.24 release published correct PyPI, npm, and Git tag version
surfaces, but the ClawHub bundle was assembled from the workflow
dispatch SHA instead of the release rewrite commit. ClawHub registry
metadata showed the requested release version while the uploaded
OpenClaw package files still contained the previous version literal,
so installed downstream packages could report the old version after an
apparently successful update.

## Location

- `.github/workflows/release.yml` — `publish-clawhub` reusable workflow inputs
- `openclaw-plugin/package.json` — file whose bundled version literal
  stayed stale when ClawHub fetched the pre-rewrite source commit

## Evidence

The v0.0.24 release job passed `version: 0.0.24` to ClawHub, and the
publish result recorded metadata version `0.0.24`. The same publish
result recorded source commit `34806dbcfa772e1f1057218960ea14171e1c3e24`.

Checking the package source at that commit shows the file payload was
still pre-release:

```console
$ curl -s https://raw.githubusercontent.com/zauberzeug/game-of-cards/34806dbcfa772e1f1057218960ea14171e1c3e24/openclaw-plugin/package.json | jq -r .version
0.0.23
```

The release tag created by the workflow points at the post-rewrite
commit and has the correct payload:

```console
$ curl -s https://raw.githubusercontent.com/zauberzeug/game-of-cards/v0.0.24/openclaw-plugin/package.json | jq -r .version
0.0.24
```

PyPI and npm were not affected: their registries reported latest
`0.0.24`, and the `v0.0.24` tag contains `0.0.24` in
`openclaw-plugin/package.json`, `openclaw-plugin/package-lock.json`,
and the Claude/Codex plugin manifests.

## What's broken

The release workflow comment treated ClawHub's reusable `version`
input as sufficient because it fixed a prior registry collision. That
only corrected the publish metadata. For the OpenClaw bundle payload,
the reusable workflow still fetched the repository at the original
workflow-dispatch SHA. In new-release mode, that SHA necessarily
precedes `scripts/release_rewrite_versions.py`, the bot commit-back,
and the `vX.Y.Z` tag.

The resulting state is internally inconsistent: ClawHub can announce
`game-of-cards@X.Y.Z`, while the installed bundle's own
`package.json` reports the previous release.

## Fix

`.github/workflows/release.yml` now exposes a build-job output that
names the source ref ClawHub should package:

- `vX.Y.Z` for real releases and tag-mode republishes
- the workflow SHA for dry-run previews, where no tag is created

`publish-clawhub` passes that ref to the ClawHub reusable workflow
along with the existing metadata `version:` input. The metadata
override remains useful, but the source ref now points at the
post-rewrite tag so the actual bundle files match the advertised
version.

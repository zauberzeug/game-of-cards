---
title: npm-tarball-ships-vendored-engine-reporting-previous-release-version
summary: "The publish-npm job checks out the pre-rewrite dispatch SHA and re-runs release_rewrite_versions.py — which deliberately skips the plugin mirrors — and never runs sync_plugin_assets.py, so every npm tarball's package.json reports the new version while the vendored engine at package/goc/__init__.py still carries the previous release's __version__ literal. Verified in the live 0.0.27 artifact, whose bundled engine reads 0.0.26. The fix lands in release.yml's publish-npm job (checkout the release tag or add a sync step) and needs a human commit."
status: open
stage: null
contribution: high
created: "2026-07-23T01:35:22Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero before the fix (skew shown) and continues to exit zero after — but with the simulation leg reporting the vendored `openclaw-plugin/goc/__init__.py` literal equal to the rewritten version (its "defect fixed" branch flipped to the pass condition), or the structural leg showing the publish-npm checkout pinned to the release tag.
  - [ ] MECHANICAL: the chosen fix (see `## Decision required`) lands in `.github/workflows/release.yml`'s publish-npm job — requires a human push; the autonomous bot's `GITHUB_TOKEN` cannot modify `.github/workflows/`.
  - [ ] EMPIRICAL: the next real release's npm tarball is downloaded from registry.npmjs.org and `package/goc/__init__.py` reads the released version (verified the way this card verified the 0.0.27/0.0.26 skew); verdict recorded in log.md.
  - [ ] MECHANICAL: the stale table row in the closed card `release-workflow-leaves-plugin-manifest-version-stale-on-main` ("npm … The publish job sees the rewritten files in its own checkout — why it works today") is amended with a forward pointer to this card, and `scripts/release_rewrite_versions.py`'s header claim that sync runs "immediately after this script" is scoped to the build job.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# npm tarball ships a vendored engine reporting the previous release's version

## Summary

The `publish-npm` job checks out the pre-rewrite dispatch SHA, re-runs
`release_rewrite_versions.py` (which by design does not touch the plugin
mirrors), and never runs `sync_plugin_assets.py` — so every npm tarball's
`package.json` says the new version while the bundled engine at
`package/goc/__init__.py` still carries the previous release's
`__version__` literal. Verified in the live 0.0.27 artifact, whose vendored
engine reads `0.0.26`.

## Location

- `.github/workflows/release.yml:641` — publish-npm's `- uses:
  actions/checkout@v6` with no `ref:`, so a release-mode dispatch from
  `main` checks out the pre-rewrite `github.sha` (mirrors still at the
  *previous* release, because mirrors only advance on main via the bot's
  release-bump commit, which happens later in the build job).
- `.github/workflows/release.yml:652-659` — step "Rewrite version literals
  from build output" runs `python3 scripts/release_rewrite_versions.py
  "$RELEASE_VERSION"`; no sync step follows in this job.
- `scripts/release_rewrite_versions.py:17-21` — mirrors are deliberately
  out of scope: "Plugin-payload mirrors (… `openclaw-plugin/goc/__init__.py`)
  are NOT touched here — they are byte-mirrored … by
  `scripts/sync_plugin_assets.py`, which the workflow runs immediately
  after this script." That "immediately after" is true only in the *build*
  job (release.yml:315), whose rewritten tree is discarded at job end.
- `openclaw-plugin/package.json:27-35` — `"files"` includes `"goc/"`, so
  the stale mirror ships in the tarball.

## What's broken

The closed card
[release-workflow-leaves-plugin-manifest-version-stale-on-main](../release-workflow-leaves-plugin-manifest-version-stale-on-main/)
declared the npm channel safe:

> | npm | publish-npm job re-runs the rewrite, then `npm publish` | The
> publish job sees the rewritten files in its own checkout |

That holds for `openclaw-plugin/package.json` (the rewrite script covers
it) but not for the vendored engine mirror `openclaw-plugin/goc/`, which
the rewrite script explicitly skips and which nothing in the publish-npm
job re-syncs. The OpenClaw plugin runs that engine via `PYTHONPATH` (not a
pip install), so `importlib.metadata.version("game-of-cards")` raises
`PackageNotFoundError` and the stale literal in `goc/__init__.py` wins.

## Empirical evidence

`uv run python .game-of-cards/deck/npm-tarball-ships-vendored-engine-reporting-previous-release-version/reproduce.py`:

```
publish-npm checkout pins a ref:        False
publish-npm re-runs the version rewrite: True
publish-npm runs sync_plugin_assets:     False
npm "files" list ships the goc/ mirror:  True
after rewrite: openclaw-plugin/package.json version  = 9.9.9
after rewrite: openclaw-plugin/goc/__init__.py       = 0.0.27
live npm 0.0.27 tarball: package.json = 0.0.27, vendored engine = 0.0.26
DEFECT REPRODUCED: publish-npm ships a vendored engine at the previous version
```

## Why it matters

Reachability: every `gh workflow run release.yml -f version=X.Y.Z` (the
canonical, documented release command) produces the skewed artifact — no
unusual input is needed. On every OpenClaw npm install, `goc --version`
reports the previous release, and the vendored engine's install/upgrade
paths stamp the stale version into consumer `.goc-version` sentinels and
`<!-- BEGIN GOC vX.Y.Z -->` markers, so downstream repos durably record a
version that was never installed. No on-main test can catch it: mirrors are
always in sync on main; the skew exists only in the publish job's ephemeral
tree, which is why `tests/test_version_surfaces.py` and the sync tripwire
both stay green across every affected release.

## Decision required

Both fixes are single-step edits to the publish-npm job in
`.github/workflows/release.yml`; a human must land either one (the
autonomous bot cannot push workflow changes):

1. **Pin the checkout to the release tag** — add `ref:
   v${{ needs.build.outputs.release_version }}` (build pushes the tag
   before publish jobs start; this mirrors the `clawhub_source_ref` fix on
   the ClawHub leg). The rewrite step becomes a harmless no-op re-check and
   the checked-out mirrors are the bot's post-sync release commit.
   Sharpest fix; couples publish-npm to the tag push having succeeded.
2. **Add a sync step** — run `python3 scripts/sync_plugin_assets.py` right
   after the rewrite step, making the job's tree self-consistent the same
   way the build job's is. Keeps the checkout semantics untouched; adds a
   second place that must remember the rewrite→sync pairing (the exact
   pairing whose omission caused this bug).

Either way, amend the superseded "why it works today" claim on the closed
predecessor card and scope the rewrite script's header comment to the build
job.

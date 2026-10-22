---
title: publish-openclaw-plugin
summary: "Publish the Game of Cards OpenClaw plugin/runtime package once `provide-openclaw-plugin-for-skills-and-hooks` lands. Distribution-only work scoped to OpenClaw. Done: npm `game-of-cards` carries 0.0.7–0.0.27 (since 2026-05-10) and ClawHub publishes from the same release run via OIDC, both versioned from the git tag like PyPI."
status: done
stage: null
contribution: medium
created: 2026-05-06
closed_at: "2026-10-22T05:11:22Z"
human_gate: none
advances:
  - support-external-game-of-cards-state-location
advanced_by:
  - provide-openclaw-plugin-for-skills-and-hooks
  - add-openclaw-install-section-to-llms-txt
  - openclaw-subagent-spawn-doesnt-project-plugin-tools
  - cut-v0-0-7-release-before-openclaw-publish
  - auto-publish-npm-and-clawhub-on-tag-push
  - publish-npm-package-under-zauberzeug-org-not-personal
  - clawhub-publish-fails-with-package-belongs-to-another-publisher
tags: [story, infra]
definition_of_done: |
  - [x] Plugin published on ClawHub (<https://clawhub.ai>) such that consumers can install via `openclaw skills install <id>`; chosen package id recorded in this card's log
  - [x] Plugin published as the npm package `game-of-cards` (name verified available on the npm registry 2026-05-09); both channels live
  - [x] Versioning policy documented relative to the `game-of-cards` PyPI package (single source of truth — npm and ClawHub track PyPI version)
  - [x] Release workflow or manual checklist exists for OpenClaw artifacts (covers ClawHub + npm)
  - [x] Published artifact installable by a fresh consumer environment with `python3` (3.10+) on PATH (no `uv` and no `pipx` step required; the plugin vendors the goc engine and uses a `bin/goc` python3 wrapper, parallel to the Claude plugin after `plugin-wrapper-drops-uv`)
  - [x] Docs link users to both install paths (ClawHub primary; npm as alternative)
  - [x] ~~Smoke test or release-verification step covers both channels~~ — **struck**: no per-channel post-publish smoke exists (the release smoke exercises the Claude plugin path); publication is verified by the registries themselves (npm lists every version, ClawHub's `publish-clawhub / publish` job reports success) and by a production OpenClaw deployment consuming the plugin. File a smoke card only if an install regression ever shows up.
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
supersedes:
  - publish-game-of-cards-agent-plugins
---

# Publish the OpenClaw plugin

## What is OpenClaw

OpenClaw is an open-source personal AI assistant (<https://github.com/openclaw/openclaw>, <https://openclaw.ai>) — Node-based, npm-distributed (`npm install -g openclaw@latest`), with a public skills registry called **ClawHub** at <https://clawhub.ai>. Skills are `SKILL.md` directories installed via `openclaw skills install`. **Distinct from OpenCode (sst/opencode).** Full identity anchor with verified upstream sources lives on `provide-openclaw-plugin-for-skills-and-hooks`.

## Why

OpenClaw plugin implementation is tracked under `provide-openclaw-plugin-for-skills-and-hooks`. Once that card lands, this card owns turning the artifact into something users can install.

## Scope

OpenClaw-only. Split out from the previous bundled card `publish-game-of-cards-agent-plugins` so each runtime publishes on its own timeline. Distribution decided 2026-05-09 on `provide-openclaw-plugin-for-skills-and-hooks`:

- ClawHub registry listing so consumers can `openclaw skills install game-of-cards`
- npm package `game-of-cards` (name verified available on the npm registry 2026-05-09; `goc` is squatted with a placeholder, so the longer name is the clean choice and also matches the PyPI name)

Both channels publish from the same artifact; npm doubles as a name-claiming step on the registry.

## Depends on

- `provide-openclaw-plugin-for-skills-and-hooks` (implementation; done)

## Outcome

Both channels are live and track PyPI from the same git tag:

- **npm** — package `game-of-cards`, 21 versions from 0.0.7
  (2026-05-10) to 0.0.27 (2026-07-14), published by the `publish-npm`
  job of `.github/workflows/release.yml` (`npm publish --provenance
  --access public`).
- **ClawHub** — package id `game-of-cards`, installed with
  `openclaw skills install game-of-cards` (README.md:45). Published by
  the `publish-clawhub` leg via OIDC trusted publishing, re-dispatched
  on the release tag (v0.0.27: run 29305647155, `publish-clawhub /
  publish: success`).
- **Versioning** — `scripts/release_rewrite_versions.py` rewrites
  `openclaw-plugin/package.json` from the release version, so npm and
  ClawHub carry the PyPI version (AGENTS.md, release section).
- **Install prerequisite** — only `python3` (3.10+): the tool handler
  runs the bundled engine as `python3 -m goc.cli` with `PYTHONPATH` on
  the vendored package (`openclaw-plugin/index.ts`), documented in
  `openclaw-plugin/README.md` § Prerequisite.
- **Docs** — `openclaw-plugin/README.md` § Install names ClawHub first
  and npm as the alternative.

The per-channel smoke item is struck (see the DoD). The 2026-07-13
hygiene note that "publish itself has not happened" was wrong: npm
had carried the package since 2026-05-10.

## Decision

*Resolved 2026-10-22T05:10:47Z:* Close as done: both channels are live (npm game-of-cards 0.0.7-0.0.27, ClawHub via the OIDC release leg); strike the per-channel smoke item

*Reasoning:* The maintainer approved the retirement in a human session on 2026-10-22 after a code and registry check showed every publication item met; the 2026-07-13 hygiene note claiming publish never happened was wrong


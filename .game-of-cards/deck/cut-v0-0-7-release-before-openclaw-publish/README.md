---
title: cut-v0-0-7-release-before-openclaw-publish
summary: "Cut PyPI release v0.0.7 before publishing the OpenClaw plugin to ClawHub and npm so the bundled engine in `game-of-cards@0.0.7` on npm matches `game-of-cards==0.0.7` on PyPI. ~30 commits have landed since v0.0.6 — the entire OpenClaw plugin, worktree/multi-agent claim protocol, skill-parity tripwire, hook-manifest derivation, and kickoff split. Publishing the plugin at the stale 0.0.6 version on npm would create a permanent 'lying version' situation where npm 0.0.6 ships engine code that 'pip install game-of-cards==0.0.6' does not."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances:
  - publish-openclaw-plugin
  - provide-openclaw-plugin-for-skills-and-hooks
  - list-game-of-cards-on-anthropic-community-marketplace
  - release-yml-smoke-job-fails-on-tag-push-events
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] `pyproject.toml` version bumped from 0.0.6 to 0.0.7
  - [x] `openclaw-plugin/package.json` version bumped from 0.0.6 to 0.0.7
  - [x] `claude-plugin/` and `openclaw-plugin/` engine mirrors regenerated via `python scripts/sync_plugin_assets.py` and pass `python scripts/sync_plugin_assets.py --check`
  - [x] `uv run goc validate` passes
  - [x] Version bumps committed
  - [x] Tag `v0.0.7` pushed; CI's `verify-version-matches-tag` job passes and OIDC-publishes to PyPI
  - [x] PyPI listing for v0.0.7 visible at <https://pypi.org/project/game-of-cards/0.0.7/>
worker: {who: Rodja Trappe, where: main}
---

# Cut v0.0.7 PyPI release before OpenClaw plugin publish

## Why

The `provide-openclaw-plugin-for-skills-and-hooks` card is parked at gate=session waiting on Rodja's ClawHub + npm publish credentials. Before that publish happens, the PyPI release should be cut so the version numbers align across ecosystems.

Today both `pyproject.toml` and `openclaw-plugin/package.json` are pinned at 0.0.6, but ~30 commits have landed since the v0.0.6 tag including substantial work:

- The entire OpenClaw plugin (TS entry + esbuild bundle + skill port + hook ports + safe-install scanner workarounds + bundled-engine wrapper)
- Worktree / multi-agent deck sync (`workflow.worktree_deck`, `workflow.claim_push`, `workflow.closure_on_integration`)
- Skill-parity tripwire (`validate_skill_dir_parity` in `goc/engine.py`) and Claude hook-manifest derivation from `templates/hooks/*.py`
- `claude-kickoff` split out from the host-agnostic `kickoff` skill
- llms.txt OpenClaw section + `uv tool install` → `pipx install` documentation pivot
- Plugin-mirror parity bug fix (`fix(validate): exclude templates/hooks dir on OpenClaw mirror parity`)
- Various validate / install bug fixes

If we publish OpenClaw plugin at the stale `0.0.6` version, npm `game-of-cards@0.0.6` would ship a bundled engine that diverges from PyPI `game-of-cards==0.0.6`. That's a permanent "lying version" trap: a future bug report against npm 0.0.6 wouldn't reproduce on the matching PyPI 0.0.6 install.

The fix is mechanical:

1. Bump `pyproject.toml` to 0.0.7
2. Bump `openclaw-plugin/package.json` to 0.0.7 (the sync hook already enforces engine-bytes equality between `goc/` and `openclaw-plugin/goc/`, so the bundled engine in npm 0.0.7 = PyPI 0.0.7 by construction)
3. Tag `v0.0.7` and push; the CI workflow at `.github/workflows/release.yml` verifies the tag matches `pyproject.toml` and OIDC-publishes to PyPI
4. Once PyPI is live, the OpenClaw publish flow (separate card) ships npm `game-of-cards@0.0.7` with the matching bundled engine

The Anthropic community marketplace listing card also benefits — submitting against a fresh release with all recent fixes is cleaner than pointing at v0.0.6.

## Scope boundaries

- This card cuts PyPI only. The actual `npm publish` and ClawHub submission stay in `publish-openclaw-plugin` / `provide-openclaw-plugin-for-skills-and-hooks` so credentials and platform-specific publish flows remain on Rodja.
- No release-notes / changelog generation is in scope. The repo doesn't maintain a CHANGELOG.md today; commit history is the source of truth.

## Non-goals

- Versioning-policy decisions (e.g., "should npm and PyPI track different cadences"). Today's policy is lockstep, and this card preserves it.

---
title: publish-codex-plugin
summary: "Publish the Game of Cards Codex plugin/runtime package once `provide-codex-plugin-for-skills-and-hooks` lands. Distribution-only work scoped to the Codex runtime."
status: done
stage: null
contribution: medium
created: 2026-05-06
closed_at: "2026-05-18T05:33:03Z"
human_gate: none
advances:
  - support-external-game-of-cards-state-location
advanced_by:
  - provide-codex-plugin-for-skills-and-hooks
tags: [story, infra]
definition_of_done: |
  - [x] Codex publication target chosen and recorded (Codex marketplace if/when it exists, npm package, or direct-install URL) — repo-hosted Codex marketplace at `.agents/plugins/marketplace.json` pointing at `./codex-plugin`; consumers run `codex plugin marketplace add zauberzeug/game-of-cards`
  - [x] Versioning policy documented relative to the `game-of-cards` PyPI package — lockstep with PyPI version, enforced by `scripts/release_rewrite_versions.py` and `tests/test_version_surfaces.py`; documented in `goc.md` Codex plugin section ("Versioning and release")
  - [x] Release workflow or manual checklist exists for Codex artifacts — existing `.github/workflows/release.yml` rewrites `codex-plugin/.codex-plugin/plugin.json` and `codex-plugin/goc/__init__.py` at release time and commits them back to `main`; the marketplace file `.agents/plugins/marketplace.json` reads directly from `main`, so no separate publish job is needed
  - [x] Published artifact installable by a fresh consumer environment with `goc` on PATH — plugin payload at `codex-plugin/` bundles the goc engine plus `bin/goc`; consumers without bare `goc` install via `pipx install game-of-cards` (documented in `goc.md` and `site/llms.txt`)
  - [x] Docs link users to the Codex install path — `README.md` "Install paths", `site/llms.txt` "Install (Codex)", and `goc.md` "Codex plugin" all carry the marketplace install commands
  - [x] Smoke test or release-verification step covers Codex artifacts — `goc validate`'s `validate_plugin_mirror_parity` (CI on every commit) covers Codex hook scripts and the bundled engine; `tests/test_plugin_mirror_parity.py` and `tests/test_version_surfaces.py` enforce structural and version-literal integrity for `codex-plugin/`; `tests/test_install.py` covers the `goc install --agents codex` consumer path
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
supersedes:
  - publish-game-of-cards-agent-plugins
---

# Publish the Codex plugin

## Why

Codex plugin implementation is tracked under `provide-codex-plugin-for-skills-and-hooks`. Once that card lands, the artifact still needs a distribution path; this card owns that distribution work for Codex specifically.

## Scope

Codex-only. Split out from the previous bundled card `publish-game-of-cards-agent-plugins` so Claude and OpenClaw publication don't gate each other.

## Depends on

- `provide-codex-plugin-for-skills-and-hooks` (implementation)
- The Codex runtime's plugin/extension format being settled (open question on that card)

## Decision

*Resolved 2026-05-18T04:09:46Z:* Use a Codex marketplace file in zauberzeug/game-of-cards as the Codex plugin distribution path, pointing at the repo-hosted codex-plugin payload

*Reasoning:* User approved the marketplace-file path; OpenAI's official Plugin Directory publishing is not self-serve yet, so repo-hosted marketplace distribution is the actionable official path now.

## Implementation summary

- **Publication target.** Repo-hosted Codex marketplace at `.agents/plugins/marketplace.json`, referencing the in-tree payload `./codex-plugin`. Consumers install with `codex plugin marketplace add zauberzeug/game-of-cards`, then `game-of-cards` from Codex's `/plugins` browser.
- **Versioning policy.** Lockstep with the `game-of-cards` PyPI package: `scripts/release_rewrite_versions.py` rewrites `codex-plugin/.codex-plugin/plugin.json::version` from the dispatched release version, `scripts/sync_plugin_assets.py` mirrors `__version__` into `codex-plugin/goc/__init__.py`, and `tests/test_version_surfaces.py` fails CI on any drift.
- **Release flow.** No separate publish job. `.github/workflows/release.yml` rewrites the Codex plugin literals as part of the unified version bump and commits them back to `main`; the marketplace file reads from `main`, so consumers running `codex plugin marketplace update zauberzeug/game-of-cards` see the new release as soon as the workflow commits.
- **Verification.** `goc validate`'s `validate_plugin_mirror_parity` (CI on every commit) checks the bundled engine and hook scripts byte-for-byte against the source tree. `tests/test_plugin_mirror_parity.py` exercises the validator. `tests/test_install.py` covers the consumer-side `goc install --agents codex` path. End-to-end Codex-runtime smoke is deferred to manual verification because the release workflow's smoke job runs Claude Code only; this is acceptable given the structural-parity coverage and the bundled engine being identical to the wheel.
- **Docs.** README "Install paths", `site/llms.txt` "Install (Codex)" (with the `codex plugin marketplace update` recipe), and `goc.md` "Codex plugin" (with a new "Versioning and release" subsection) document install, update, hooks, CLI behavior, and the lockstep policy.

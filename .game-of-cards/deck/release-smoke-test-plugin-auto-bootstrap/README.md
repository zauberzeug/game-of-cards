---
title: release-smoke-test-plugin-auto-bootstrap
summary: "Add an automated end-to-end smoke test that runs before a release tag publishes — spin up Claude Code headlessly in an empty temp dir, install the plugin from the marketplace, invoke a skill, and assert the bootstrap routing flow correctly handles missing CLI / missing permission allowance / missing project state."
status: open
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: session
advances: [publish-claude-code-plugin]
advanced_by: [publish-claude-code-plugin]
tags: [story, infra]
definition_of_done: |
  - [ ] Workflow design decided: GitHub Actions step in `release.yml` triggered on tag push *before* the PyPI publish step, OR a separate `pre-release.yml` triggered on a candidate-tag pattern (e.g. `v*-rc*`)
  - [ ] Headless Claude Code invocation pattern verified — `claude -p` (or equivalent flag) supports running slash commands like `/plugin marketplace add` and `/plugin install` without an interactive session
  - [ ] Test harness creates an empty temp dir with no goc CLI on PATH and no pre-existing `.game-of-cards/`, then runs Claude Code with a structured prompt ("install the plugin, invoke `/extend-deck`, report what happened")
  - [ ] Pre-seeded `~/.claude/settings.json` strategy chosen — pre-grant `Bash(goc:*)` (skips bootstrap Step 3 but tests Steps 1+2+4) OR leave unset and assert the LLM emits the bootstrap remediation text (tests routing but can't complete install)
  - [ ] Assertions implemented — output contains `Skill(bootstrap)` reference when expected; if pre-seeded with allowance, `.game-of-cards/deck/` is created in the temp dir and a follow-up skill call resolves
  - [ ] CI secret `ANTHROPIC_API_KEY` documented in repo secrets; cost ceiling estimated and documented in workflow comments
  - [ ] Local-dev runner exists (`scripts/smoke_release.sh` or equivalent) so the test can be exercised before pushing a tag
  - [ ] Workflow fails the release if any assertion fails; passing the smoke test gates the PyPI publish
---

# Release-time auto-bootstrap smoke test

## Why

The 2026-05-07 publish session caught **four** real shipping defects in
sequence — symlinked plugin assets stripped during marketplace install,
stale marketplace cache, skill-body shim path resolution, and bash-policy
denial of `goc` invocation — none of which were visible to the existing
unit tests. Each was caught only by Rodja running the plugin manually
in a real Claude Code session. That's exactly the kind of surface that
costs a release if it regresses, and the kind of confidence an automated
end-to-end check is supposed to deliver.

This card adds that check, runs it on the release tag, and refuses to
publish 0.0.7 (and every release after) unless the plugin actually
installs and bootstraps cleanly in a virgin environment.

## What "works" means in the smoke test

A pass means a fresh consumer environment can:

1. `/plugin marketplace add zauberzeug/game-of-cards` — marketplace clone
   succeeds against the published tag's commit
2. `/plugin install game-of-cards@game-of-cards` — install cache contains
   all 12 skills + 3 hooks as real files (not orphan symlinks)
3. Invoke any skill that uses goc (e.g. `/extend-deck`)
4. Either:
   - **Path A (allowance pre-seeded)**: skill runs end-to-end against a
     clean temp dir, bootstrap fires for the missing project state, and
     `.game-of-cards/deck/` is created
   - **Path B (allowance absent)**: the `!`-block fails as expected, but
     the LLM correctly routes to `Skill(bootstrap)` and bootstrap surfaces
     the verbatim instructions to add `Bash(goc:*)` to settings

Path A is the higher-fidelity test (covers more of the bootstrap chain).
Path B is what an unprepared consumer actually experiences, so it's the
one that catches preflight regressions. Probably worth running both as
two separate steps.

## Open design questions (session required)

1. **Trigger point.** Pre-tag (run on every push to main, slow CI) vs
   on-tag-before-publish (only at release, but blocks the release). The
   on-tag-before-publish shape matches the user's ask but means a failed
   smoke means a botched release artifact (no PyPI publish, but tag
   exists). Mitigation: use a candidate-tag pattern (`v*-rc*`) that
   only publishes after smoke passes, then promote to `v*`.

2. **API cost ceiling.** Each run is 1 Claude session, probably ~5–10
   tool turns. Need order-of-magnitude estimate before wiring secret.

3. **Pre-seeded allowance.** If we pre-seed `Bash(goc:*)`, we lose
   coverage of the bootstrap-Step-3 (permission-routing) path that just
   landed in `247d8c0`. If we don't pre-seed, the LLM can't actually
   install goc and complete the bootstrap, so the test only verifies
   "Skill(bootstrap) gets invoked" not "bootstrap actually works." Two
   separate steps with different settings probably resolves this.

4. **Headless slash commands.** Need to verify whether `claude -p` (or
   whatever the headless flag is) supports the `/plugin marketplace add`
   and `/plugin install` slash commands. If not, fall back to manually
   pre-cloning the marketplace cache to simulate the install.

5. **Local-dev runnable.** Should mirror the CI step exactly, runnable
   via `make smoke` or `./scripts/smoke_release.sh`. Same Claude CLI,
   same prompt fixture, just different secret source.

## Notes

- This advances `publish-claude-code-plugin` (now closed) by mechanizing
  the smoke-test box that was satisfied manually for 0.0.6.
- Companion to (but distinct from) the existing CI tripwire that checks
  `claude-plugin/` matches `goc/templates/` byte-for-byte. That tripwire
  is fast and runs every push; this one is expensive and runs on tag.

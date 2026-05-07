---
title: release-smoke-test-plugin-auto-bootstrap
summary: "Add an automated end-to-end smoke test that runs before a release tag publishes — spin up Claude Code headlessly in an empty temp dir, install the plugin from the marketplace, invoke a skill, and assert the bootstrap routing flow correctly handles missing CLI / missing permission allowance / missing project state."
status: active
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: none
advances: [publish-claude-code-plugin]
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] Workflow design decided: `smoke` job added to `.github/workflows/release.yml` between `build` and `publish`; `publish.needs: [build, smoke]` so a failed smoke blocks PyPI publish on the tag
  - [x] Headless Claude Code invocation pattern verified — slash commands are interactive-only; switched to `claude --plugin-dir <path> -p` which loads the plugin from the local checkout and bypasses the marketplace cache (the marketplace path stays manual until Claude Code adds headless slash-command support; symlink-strip class is already covered by the byte-for-byte tripwire in `ci.yml`)
  - [x] Test harness creates an empty temp dir (`/tmp/smoke-A`, `/tmp/smoke-B`) with `git init` and no `.game-of-cards/`; the workflow steps "Set up Path A workspace" and "Set up Path B workspace" do this
  - [x] Pre-seeded allowance strategy: both Path A (allowance pre-seeded via `--allowedTools "Bash(goc:*)..."` + `goc` pre-installed) and Path B (allowance absent + `goc` not allowed) run as separate steps — see release.yml `smoke` job
  - [x] Assertions implemented — Path A asserts `/tmp/smoke-A/.game-of-cards/deck/` exists AND `result.txt` contains `A:passed`; Path B asserts `result.txt` contains `B:passed`. Both assertions are filesystem-based, not LLM-self-report
  - [x] Auth surface: reuses `CLAUDE_CODE_OAUTH_TOKEN` from `pull-card.yml` (no new secret); billing is the existing Claude Code subscription, not raw API tokens
  - [x] Local-dev runner: `scripts/smoke_release.sh` mirrors the workflow exactly via `claude` CLI directly; supports `./scripts/smoke_release.sh A`, `B`, or `AB` (default)
  - [x] Workflow fails the release if any assertion fails; `publish.needs: [build, smoke]` enforces the gate
  - [ ] Smoke job verified by running v0.0.7-test or a `workflow_dispatch` invocation and confirming Path A + Path B both pass against real Claude Code action behavior (uncertainty around `--plugin-dir` flag passthrough and `Skill(...)` allowedTools syntax — needs a live run to confirm)
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

## Constraints from Claude Code headless mode

Investigated 2026-05-07 against https://code.claude.com/docs/en/headless and
https://code.claude.com/docs/en/permission-modes:

- **Slash commands are interactive-only**: `/plugin marketplace add` and
  `/plugin install` do **not** execute in `claude -p` headless mode. There
  is no `claude plugin install` CLI subcommand either.
- **Workaround**: `claude --plugin-dir ./claude-plugin -p "<prompt>"` loads
  the plugin directly from a local path. That bypasses the marketplace
  cache entirely and tests the *plugin payload as it sits on disk*.
- **Permission policy is fully active in headless**: use
  `--permission-mode dontAsk --allowedTools "Bash(goc:*),Read"` to enforce
  a known allowlist without prompts.
- **API**: bills against `ANTHROPIC_API_KEY`. `--bare` skips OAuth and
  local-config discovery for reproducible runs.

This means the smoke test cannot exercise the *marketplace-install* path
end-to-end — that part stays manual until Claude Code adds headless
slash-command support. But it **can** exercise:
- Plugin payload loads cleanly from a `--plugin-dir` checkout (no broken
  symlinks, all 12 skills + 3 hooks discoverable)
- Skill `!`-blocks render correctly (preflight section visible to the
  LLM, no `_goc-bootstrap.sh` references leaking back in)
- Bootstrap routing fires when goc is missing or denied (Path B)
- Bootstrap completes when goc + allowance are pre-seeded (Path A)

The marketplace-install path is partially covered today by the
byte-for-byte tripwire in `ci.yml` ("Verify plugin assets match templates")
which catches the symlink-strip class of bug at every push. Stale
marketplace cache UX remains manual.

## Remaining design questions (session required)

1. **Trigger point.** On-tag-before-publish blocks broken releases but
   means a failed test leaves the tag without artifacts. Candidate-tag
   pattern (`v*-rc*` runs smoke, `v*` only after green) is safer but
   adds workflow complexity. Or run on every push to main and gate the
   release on the latest main being green (cheapest user effort, highest
   CI cost).

2. **API cost ceiling.** Each run is ~1 Claude session, ~5–15 tool turns,
   ~30k–100k tokens. Need user concurrence on running per-tag.

3. **Path A vs B coverage.** Run both as separate workflow steps?
   - Step A pre-seeds `Bash(goc:*)`, installs goc, asserts bootstrap
     completes and `.game-of-cards/deck/` is created.
   - Step B leaves the allowance unset, asserts the `!`-block fails
     and the LLM emits the bootstrap remediation text. Both steps are
     valuable; both cost API tokens.

4. **Local-dev runner.** `scripts/smoke_release.sh` mirrors the CI step
   exactly. Useful for iterating without burning CI minutes.

## Notes

- This advances `publish-claude-code-plugin` (now closed) by mechanizing
  the smoke-test box that was satisfied manually for 0.0.6.
- Companion to (but distinct from) the existing CI tripwire that checks
  `claude-plugin/` matches `goc/templates/` byte-for-byte. That tripwire
  is fast and runs every push; this one is expensive and runs on tag.

## Decision

*Resolved 2026-05-07:* Trigger on v* tag, gating PyPI publish; run both Path A (full bootstrap with allowance pre-seeded) and Path B (routing-only with allowance absent) as separate steps; reuse anthropics/claude-code-action@v1 with the existing CLAUDE_CODE_OAUTH_TOKEN

*Reasoning:* Tag-blocking matches the user's explicit ask and a botched tag without artifacts is a recoverable inconvenience vs. a broken release reaching PyPI; both paths cover distinct regression surfaces (preflight routing vs. bootstrap completeness); reusing pull-card.yml's auth surface adds zero new secrets and zero new billing exposure

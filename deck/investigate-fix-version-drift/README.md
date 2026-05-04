---
title: investigate-fix-version-drift
summary: "Find and fix the repo's self-hosted version drift: generated marker blocks and user-facing docs still mention older releases while the package reports the current version."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: []
advanced_by: []
tags: [infra, documentation]
definition_of_done: |
  - [x] Inventory every public version surface (`pyproject.toml`, `goc.__version__`, README status text, AGENTS/CLAUDE marker blocks, `deck/.goc-version`, release docs) and classify intentional historical mentions vs live drift
  - [x] Decide the self-hosted upgrade rule: whether `goc upgrade` must be run as part of every version bump, or whether CI should detect stale generated blocks
  - [x] Apply the fix so the dogfood copy reports the current package version everywhere live user guidance expects it
  - [x] Add or document a smoke check that would catch stale marker blocks / sentinel drift before release
  - [x] `goc validate` passes after the version cleanup
---

# investigate-fix-version-drift

## Why

The package currently reports `0.0.2`, while the repo's installed
GoC marker blocks and `deck/.goc-version` can still reflect older
install state. That makes the dogfood copy look stale and weakens the
claim that consumers should trust `goc upgrade` to round-trip generated
methodology text.

## Scope

Treat historical release records in `deck/` as archival unless they are
used as current user guidance. Fix live docs, generated sections, and
the self-hosted sentinel. Capture the rule that prevents this from
recurring on the next version bump.

## Inventory

Live surfaces checked on 2026-05-04:

- `pyproject.toml` reports package version `0.0.2`.
- `goc.__version__` reports `0.0.2`.
- `deck/.goc-version` contains `0.0.2`.
- `AGENTS.md` marker block is `<!-- BEGIN GOC v0.0.2 -->`.
- `CLAUDE.md` marker block is `<!-- BEGIN GOC v0.0.2 -->`.
- README `Status` no longer hard-codes `0.0.1`; it describes alpha status
  without embedding a drift-prone version number.
- `.github/workflows/release.yml` already verifies tag version against
  `pyproject.toml` before publishing.

Historical/archival mentions intentionally left alone:

- Closed deck cards documenting old release plans or prior evidence, including
  `install-command-scaffolds-repo`, `package-pyproject-and-pypi-release`, and
  `readme-starter-card-and-doc-polish-session`.

## Decision

Use CI detection rather than requiring every version bump to remember a manual
`goc upgrade` step. A version bump is allowed to update generated marker blocks
through `goc upgrade`, but the load-bearing rule is: tests fail if any live
self-hosted version surface drifts from the package version.

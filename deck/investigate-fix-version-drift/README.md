---
title: investigate-fix-version-drift
summary: "Find and fix the repo's self-hosted version drift: generated marker blocks and user-facing docs still mention older releases while the package reports the current version."
status: active
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra, documentation]
definition_of_done: |
  - [ ] Inventory every public version surface (`pyproject.toml`, `goc.__version__`, README status text, AGENTS/CLAUDE marker blocks, `deck/.goc-version`, release docs) and classify intentional historical mentions vs live drift
  - [ ] Decide the self-hosted upgrade rule: whether `goc upgrade` must be run as part of every version bump, or whether CI should detect stale generated blocks
  - [ ] Apply the fix so the dogfood copy reports the current package version everywhere live user guidance expects it
  - [ ] Add or document a smoke check that would catch stale marker blocks / sentinel drift before release
  - [ ] `goc validate` passes after the version cleanup
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

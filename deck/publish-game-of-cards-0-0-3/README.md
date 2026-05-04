---
title: publish-game-of-cards-0-0-3
summary: "Publish Game of Cards 0.0.3 to PyPI from the verified main branch, carrying the CI install fix and current README/package metadata."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [x] Version surfaces report 0.0.3 (`pyproject.toml`, `goc.__version__`, self-hosted GoC markers)
  - [x] Local test suite passes
  - [x] Distribution artifacts build successfully
  - [x] Git tag `v0.0.3` is pushed and `0.0.3` is live on PyPI
---

# Publish Game of Cards 0.0.3

## Summary

PyPI's canonical JSON endpoint reports `game-of-cards` latest as `0.0.2`.
The local repo is ready for a patch release that includes the CI package
install fix and the current PyPI-facing README/package metadata.

## Release Plan

1. Bump live package/version surfaces from `0.0.2` to `0.0.3`.
2. Run the local release checks: pytest, deck validation, and `uv build`.
3. Commit the release-prep changes and close this card.
4. Create and push tag `v0.0.3`. The existing GitHub Actions release
   workflow verifies the tag matches `pyproject.toml` and should publish via
   PyPI trusted publishing; `0.0.3` was manually published because the PyPI
   trusted publisher was not configured yet.

## Why It Matters

The public `0.0.2` package predates the latest CI workflow fix. Publishing
`0.0.3` gives users the current installer/test workflow and exercises the
tag-triggered release pipeline now present in the repo.

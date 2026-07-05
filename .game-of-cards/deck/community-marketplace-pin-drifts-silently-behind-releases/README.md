---
title: community-marketplace-pin-drifts-silently-behind-releases
status: active
stage: null
contribution: medium
created: "2026-07-05T17:36:32Z"
closed_at: null
human_gate: none
advances:
  - list-game-of-cards-on-anthropic-community-marketplace
advanced_by: []
tags: [infra]
definition_of_done: |
  - [ ] EMPIRICAL: A scheduled workflow compares the `game-of-cards` pin in
    `anthropics/claude-plugins-community` against the latest release commit
    and flags drift.
  - [ ] EMPIRICAL: Drift produces exactly one open tracking issue (created once,
    updated in place on later runs — no duplicate issues per run).
  - [ ] EMPIRICAL: The tracking issue closes automatically once the marketplace pin
    contains the latest release commit.
  - [ ] EMPIRICAL: A fresh release inside the grace window does not fire a false alarm
    (the nightly marketplace sync gets time to catch up).
  - [ ] MECHANICAL: Repos without a published release, and a delisted marketplace entry,
    exit cleanly / flag explicitly instead of erroring cryptically.
  - [x] MECHANICAL: The release.yml header documents the marketplace-pin follow-up so
    release operators know the distribution chain does not end at publish.
  - [x] PROCESS: `uv run goc validate` passes.
---

# community-marketplace-pin-drifts-silently-behind-releases

## Why

Issue [#6](https://github.com/zauberzeug/game-of-cards/issues/6): the
Anthropic community marketplace (`anthropics/claude-plugins-community`)
pins plugin sources to an exact commit sha. Our entry was pinned to
`4e4c5a1` (2026-05-11) — *before* the strict-YAML frontmatter fix
`2f1ba0a5` (released in v0.0.24) — so `claude plugin validate` failed for
marketplace users while `main` and every release since v0.0.24 were clean.
Nobody on our side noticed until the marketplace maintainers filed the
issue: the pin drifts silently.

The marketplace repo is a **read-only mirror** — direct PRs are closed
automatically; entries sync nightly from Anthropic's internal review
pipeline (submission via `clau.de/plugin-directory-submission`). So we
cannot push the re-pin ourselves; we can only *detect* drift and prompt a
human to coordinate/re-submit.

## Design

New workflow `.github/workflows/marketplace-pin-check.yml`:

- **Triggers:** daily schedule (after Anthropic's nightly sync window) +
  `workflow_dispatch`.
- **Check:** resolve the latest release tag to its commit
  (`repos/{repo}/commits/{tag}` derefs annotated tags — the v0.0.26 tag
  object `b6d5a79` vs commit `d19aa09a` distinction from #6), fetch the
  marketplace `source.sha` for `game-of-cards`, then
  `repos/{repo}/compare/{release}...{pin}`: status `identical`/`ahead`
  → pin contains the release → fresh; `behind`/`diverged` → stale.
- **Grace window:** a release younger than 48h is not flagged, so the
  nightly sync can catch up before we open an issue.
- **Signal:** one labelled tracking issue (`marketplace-pin`), created
  once and updated in place; closed automatically when the pin catches
  up. Loud failure over silent skip: a delisted entry flags too.

## Verification

- `python3 -c "import yaml,sys;..."` — workflow YAML parses (see log.md).
- Check logic dry-run against live GitHub data at authoring time:
  latest release v0.0.26 → commit `d19aa09a`, marketplace pin `4e4c5a1`,
  compare status `behind` → stale → would open the tracking issue. ✓
- False-alarm path: compare `d19aa09a...d19aa09a` → `identical` → fresh. ✓

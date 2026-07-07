---
title: community-marketplace-pin-drifts-silently-behind-releases
status: done
stage: null
contribution: medium
created: "2026-07-05T17:36:32Z"
closed_at: "2026-07-07T01:09:20Z"
human_gate: none
advances:
  - list-game-of-cards-on-anthropic-community-marketplace
advanced_by:
  - marketplace-pin-check-crashes-on-repos-without-version-tags
tags: [infra]
definition_of_done: |
  - [x] EMPIRICAL: A scheduled workflow compares the `game-of-cards` pin in
    `anthropics/claude-plugins-community` against the latest release commit
    and flags drift.
  - [x] EMPIRICAL: Drift produces exactly one open tracking issue (created once,
    updated in place on later runs — no duplicate issues per run).
  - [x] EMPIRICAL: The tracking issue closes automatically once the marketplace pin
    contains the latest release commit.
  - [x] EMPIRICAL: A fresh release inside the grace window does not fire a false alarm
    (the nightly marketplace sync gets time to catch up).
  - [x] MECHANICAL: A delisted marketplace entry flags explicitly instead of
    erroring cryptically. (No-release-repo robustness re-scoped to
    `marketplace-pin-check-crashes-on-repos-without-version-tags`: the one-line
    fix is authored and verified but the autonomous bot cannot push
    `.github/workflows/` changes, and the path is unreachable in this repo —
    version tags always exist.)
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

Every DoD path has been exercised against the real workflow script
(the local runs execute the exact `run:` block extracted from the
committed workflow YAML, with env overrides only):

- **Drift detection + issue creation (real CI, scheduled):** run
  [28787589943](https://github.com/zauberzeug/game-of-cards/actions/runs/28787589943)
  (2026-07-06) compared v0.0.26 → `d19aa09a` against pin `4e4c5a1`,
  got `behind`, and opened tracking issue
  [#8](https://github.com/zauberzeug/game-of-cards/issues/8). ✓
- **Update-in-place, no duplicates (real CI, dispatch):** run
  [28834156281](https://github.com/zauberzeug/game-of-cards/actions/runs/28834156281)
  (2026-07-07) found #8 open, edited its body in place; exactly one
  `marketplace-pin` issue exists after two flagging runs. ✓
- **Auto-close (local, test label):** with a mocked marketplace JSON
  pinning `d19aa09a` (compare → `identical`), the script auto-closed
  the open test issue #9 under the temporary `marketplace-pin-test`
  label — real tracker #8 untouched. #8 will close the same way once
  the live pin catches up. ✓
- **Grace window (local, clock shim):** live stale pin + `date +%s`
  shimmed to 1h after the v0.0.26 tag commit → "release is only 1h
  old (< 48h grace) — not flagging yet", exit 0, no issue ops. ✓
- **No-release repo (local):** this path was found broken — a repo
  with no `vX.Y.Z` tags dies with a bare exit 1 (`grep` finding no
  tags fails the pipeline under `set -euo pipefail` before the
  empty-tag guard runs). The one-line `|| true` fix is authored and
  verified locally, but the autonomous bot's token cannot push
  `.github/workflows/` changes, so it is re-scoped to
  [`marketplace-pin-check-crashes-on-repos-without-version-tags`](../marketplace-pin-check-crashes-on-repos-without-version-tags/)
  (human-gated). Unreachable in this repo: version tags always exist. ⚠
- **Delisted entry (local, test label):** mocked marketplace JSON
  without the `game-of-cards` entry → explicit "entry is missing
  (delisted?)" flag and a tracking issue, not a cryptic error. ✓

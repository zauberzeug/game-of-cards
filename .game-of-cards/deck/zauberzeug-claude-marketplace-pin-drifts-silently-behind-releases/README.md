---
title: zauberzeug-claude-marketplace-pin-drifts-silently-behind-releases
summary: "The zauberzeug-claude marketplace pins game-of-cards to a fixed tag (ref: v0.0.25), so Claude Code installs sourced from it silently skip every new release — v0.0.26 and v0.0.27 never reached consumers. Second instance of the pin-drift pattern fixed for the Anthropic community marketplace; this marketplace is Zauberzeug-owned, so the pin is directly fixable, but the durable mechanism (bump per release vs. float vs. extend the pin-check workflow) needs a maintainer decision."
status: open
stage: null
contribution: medium
created: "2026-07-14T04:30:10Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [ ] MECHANICAL: The zauberzeug-claude marketplace resolves game-of-cards
    to v0.0.27 or later (pin bumped or replaced by a floating ref).
  - [ ] EMPIRICAL: `claude plugin marketplace update zauberzeug-claude` followed
    by `claude plugin update game-of-cards@zauberzeug-claude` lands 0.0.27+ in
    the local plugin cache (verify the version dir under
    `~/.claude/plugins/cache/zauberzeug-claude/game-of-cards/`).
  - [ ] PROCESS: The decision (per-release bump vs. floating ref vs. pin-check
    extension) is recorded via `goc decide` with the why; if the pin-check
    extension is chosen, the follow-up work is filed as its own card.
  - [ ] MECHANICAL: The release flow documentation (release.yml header and/or
    AGENTS.md release section) names this marketplace as a post-release
    propagation step, so the next release operator does not rediscover it.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# zauberzeug-claude-marketplace-pin-drifts-silently-behind-releases

## Why

Second instance of the pattern closed in
[community-marketplace-pin-drifts-silently-behind-releases](../community-marketplace-pin-drifts-silently-behind-releases/):
a downstream marketplace pins the plugin to a fixed git ref, so
publishing a release moves PyPI/npm/ClawHub and the literals on `main`
but leaves that marketplace's consumers stranded — silently, because
nothing on our side watches the pin.

This time the marketplace is `zauberzeug/zauberzeug-claude` (the
Zauberzeug-internal Claude Code marketplace), whose `marketplace.json`
sources game-of-cards as:

```json
"source": {
  "source": "git-subdir",
  "url": "https://github.com/zauberzeug/game-of-cards.git",
  "path": "claude-plugin",
  "ref": "v0.0.25"
}
```

## What's broken

The pin froze at `v0.0.25`. Both v0.0.26 (2026-07-01) and v0.0.27
(2026-07-14) shipped without moving it, so every Claude Code install
sourced from this marketplace kept resolving v0.0.25. Observed on a
maintainer machine on 2026-07-14, immediately after the v0.0.27
release:

- `installed_plugins.json` shows `game-of-cards@zauberzeug-claude` at
  `version: 0.0.25` for both the user-scope install and a
  project-local install, `lastUpdated: 2026-06-26`.
- The marketplace snapshot itself had refreshed on 2026-07-04 — three
  days after v0.0.26 — yet still resolved v0.0.25, confirming the pin
  (not snapshot staleness) is the blocker. Plugin update commands
  cannot help until the pin moves.

The existing `marketplace-pin-check.yml` workflow (deliverable of the
root card) only compares the pin in
`anthropics/claude-plugins-community`; this marketplace is invisible
to it.

Contrast: the Codex channel of the same machine had 0.0.26 and needs
only a marketplace snapshot refresh, because the repo-local
`.agents/plugins/marketplace.json` uses `source: local, path:
./codex-plugin` — no pin. The pinned Claude channel is the outlier.

## Why it matters

The zauberzeug-claude marketplace is the primary distribution path for
game-of-cards onto Zauberzeug developer machines. A silent pin means
the audience closest to the project runs the oldest code — v0.0.25
predates two releases of engine fixes — and nobody notices, exactly
the failure mode of issue #6 on the Anthropic marketplace. Unlike that
read-only mirror, this repo is Zauberzeug-owned: the fix is one commit
away, which makes silent drift purely self-inflicted.

## Decision required

How should this marketplace track releases? The options are not all
mutually exclusive (an immediate bump combines with either durable
mechanism):

1. **Bump the pin per release (manual).** Keep `ref: vX.Y.Z` for
   reproducibility; add the bump to the documented release flow.
   Cheapest now, but this card exists because the manual step was
   forgotten twice.
2. **Float the ref to `main`.** Releases propagate automatically
   (plugin managers read the git tree, and the release workflow
   commits version literals back to `main` for exactly this reason).
   Trades away the ability to hold consumers on a known-good tag.
3. **Extend `marketplace-pin-check.yml`** to also compare the
   zauberzeug-claude pin against the latest release, reusing the
   existing tracking-issue machinery. Keeps the pin, automates the
   noticing; the bump itself stays manual (or becomes a bot PR, since
   the repo is Zauberzeug-owned).

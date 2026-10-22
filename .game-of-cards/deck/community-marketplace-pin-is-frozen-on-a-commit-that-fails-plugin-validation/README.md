---
title: community-marketplace-pin-is-frozen-on-a-commit-that-fails-plugin-validation
summary: "Anthropic's community marketplace lists game-of-cards but keeps it pinned to 4e4c5a1 (2026-05-11), a commit whose skill frontmatter fails claude plugin validate, and the entry has not followed any later release despite a re-pin request in July. Users installing from the community marketplace get the broken May build. Re-submit once 0.0.29 is published, then verify a fresh install and make the community marketplace the documented install path."
status: open
stage: null
contribution: high
created: "2026-10-22T05:15:04Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [infra, documentation]
definition_of_done: |
  - [ ] PROCESS: once 0.0.29 is published to PyPI, npm and ClawHub, the plugin is re-submitted via `clau.de/plugin-directory-submission` (or the re-pin is requested again on the GitHub issue #6 thread); the submission reference is recorded in log.md
  - [ ] EMPIRICAL: the community-marketplace entry pins a commit at or after the 0.0.29 release commit — the Marketplace Pin Check workflow then closes GitHub issue #8 by itself
  - [ ] EMPIRICAL: fresh-machine smoke — a clean Claude Code profile with no prior game-of-cards install runs `/plugin marketplace add` (community marketplace) → `/plugin install game-of-cards@…` → asks the agent to file a card → the card is created; the written reproduction (steps + observed output) is recorded in log.md
  - [ ] MECHANICAL: README install path, `llms.txt`, the `CLAUDE_GOC.md` template and the homepage name the community marketplace as the canonical Claude Code install path; the zauberzeug-claude marketplace and the direct install stay documented as alternatives
  - [ ] PROCESS: `uv run goc validate` passes
---

# The community-marketplace pin is frozen on a commit that fails plugin validation

## Location

- The `game-of-cards` entry in Anthropic's community marketplace
  (`anthropics/claude-plugins-community`, a read-only mirror fed by
  Anthropic's internal pipeline; direct PRs are auto-closed). It pins an
  exact commit sha of this repo.
- `.github/workflows/marketplace-pin-check.yml` — the scheduled check
  from `community-marketplace-pin-drifts-silently-behind-releases`; it
  keeps GitHub issue #8 ("Community-marketplace pin is behind the
  latest release") open while the pin lags the latest release tag.

## What's broken

The entry pins `4e4c5a10` (2026-05-11). The skill-frontmatter fix that
makes the plugin pass `claude plugin validate` landed later, in
`2f1ba0a5` (2026-06-04, "quote strict-yaml frontmatter"). So every user
who installs game-of-cards from the community marketplace gets a build
whose skills load with empty metadata — the defect GitHub issue #6
reported.

The pin has not moved since. Other plugins in the mirror receive regular
automated `bump(<plugin>)` commits; game-of-cards does not.

## Empirical evidence

- GitHub issue #6 (opened 2026-07-06 by the community-marketplace
  maintainers): `claude plugin validate` at the listed commit fails with
  "YAML frontmatter failed to parse". The thread identifies the
  repo-side fix as `2f1ba0a5`. A re-pin to the v0.0.26 commit
  `d19aa09a388b97ee18160138dc3549f82df0e6da` was requested on 2026-07-05,
  with mirror-history evidence that the entry is frozen added on
  2026-07-06. Neither got an answer.
- GitHub issue #8 (opened 2026-10-21 by the Marketplace Pin Check):
  "The marketplace pins `4e4c5a1`, which does not contain the latest
  release `v0.0.28` … compare status: `behind`."

## Why it matters

The community marketplace is the broadest-audience Claude Code channel.
A user who discovers game-of-cards there gets the May build with broken
skill metadata — a worse first impression than not being listed. Making
the community marketplace the documented install path (the last DoD
item) only makes sense once the pin points at a working release.

This card continues
[list-game-of-cards-on-anthropic-community-marketplace](../list-game-of-cards-on-anthropic-community-marketplace/),
which closed on 2026-10-22: the listing exists, so what remains is
unfreezing the pin plus the fresh-machine smoke and the docs update
moved over from that card.

## Next steps

1. **After 0.0.29 is published** (the release is blocked on
   `denied-preamble-block-aborts-skill-load-before-the-preflight-routes-to-kickoff`):
   re-submit via `clau.de/plugin-directory-submission`, referencing
   issue #6 and the frozen pin. This is a human action — the form is
   tied to the maintainer's account, and an autonomous agent should not
   file on an Anthropic-owned channel — hence `human_gate: session`.
2. Wait for the pin to move. Issue #8 closes itself once the pin
   contains the latest release commit.
3. Run the fresh-machine smoke on a clean profile and record it.
4. Update the install docs.

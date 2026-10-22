---
title: list-game-of-cards-on-anthropic-community-marketplace
summary: "Submit the Game of Cards Claude Code plugin to Anthropic's community marketplace (`anthropics/claude-plugins-community` or the equivalent submission form at `clau.de/plugin-directory-submission`) so a broader audience discovers it without first finding the zauberzeug GitHub repo. Done: submitted via the form on 2026-05-09 and listed (GitHub issue #6), but the entry is frozen on the May commit 4e4c5a10 — unfreezing it, the fresh-machine smoke and the install-docs update continue in community-marketplace-pin-is-frozen-on-a-commit-that-fails-plugin-validation."
status: done
stage: null
contribution: high
created: 2026-05-08
closed_at: "2026-10-22T05:16:34Z"
human_gate: none
advances: []
advanced_by:
  - add-readme-to-claude-code-plugin
  - release-smoke-references-renamed-skills-fails-dry-run
  - add-plugin-update-instructions-to-marketplace-readme
  - make-kickoff-idempotent-on-restart
  - add-privacy-policy-page-for-marketplace-submission
  - lead-llms-txt-with-claude-code-plugin
  - kickoff-crashes-when-user-declines-merge-question
  - cut-v0-0-7-release-before-openclaw-publish
  - pattern-generalization-hook-missing-from-local-skills-install
  - llms-txt-still-recommends-uv-tool-install-as-preferred
  - community-marketplace-pin-drifts-silently-behind-releases
tags: [story, infra, documentation]
definition_of_done: |
  - [x] All hard prereqs closed: `add-readme-to-claude-code-plugin` (whose own prereqs `bundle-goc-engine-inside-plugin-payload` and `align-skill-names-with-agile-vocabulary` are both done; awaits Rodja's marketplace-grade sign-off on the rendered README) — done 2026-05-08, as are all eleven `advanced_by` cards.
  - [x] Decision recorded on submission channel: PR to `anthropics/claude-code-plugins` (or current canonical name) vs. form at `clau.de/plugin-directory-submission` vs. both. Capture the URL and current submission policy at decision time, since Anthropic's process may change between when the card was filed and when it's worked.
  - [x] ~~Fresh-machine smoke test passes: a clean environment with no prior `game-of-cards` install runs `/plugin marketplace add` (community marketplace) → `/plugin install game-of-cards@…` → prompts agent → agent creates a card. Zero global package installs required. Captured as a screen recording or written reproduction so the submission PR can link to it.~~ — **moved** to [community-marketplace-pin-is-frozen-on-a-commit-that-fails-plugin-validation](../community-marketplace-pin-is-frozen-on-a-commit-that-fails-plugin-validation/): a smoke against today's frozen May pin would only re-confirm the known breakage, so it runs once the pin moves.
  - [x] Version bumped intentionally if appropriate. Pre-1.0 (`0.0.x`) is acceptable for community marketplace; document the choice. If 1.0.0 is the chosen stake-in-the-ground, bump pyproject.toml + plugin.json + marketplace.json in lockstep (the existing CI tripwire enforces this).
  - [x] Submission opened (PR or form). Card transitions to `active` at this point; the worker field captures the URL of the submission.
  - [x] Submission accepted / merged. Card transitions to `done`. — accepted: GitHub issue #6 (2026-07-06), opened by the community-marketplace maintainers, refers to game-of-cards as listed there, pinned to `4e4c5a10`.
  - [x] ~~Post-merge documentation updated: README install path, `llms.txt`, `CLAUDE_GOC.md` template, and homepage all mention the community marketplace as the canonical install path. The existing zauberzeug-claude private marketplace and direct-install fallback remain documented as alternatives.~~ — **moved** to [community-marketplace-pin-is-frozen-on-a-commit-that-fails-plugin-validation](../community-marketplace-pin-is-frozen-on-a-commit-that-fails-plugin-validation/): naming the community marketplace as the canonical path would send users to the frozen pin, whose skills fail `claude plugin validate`.
  - [x] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# List Game of Cards on Anthropic's community marketplace

## Why

Today's distribution channels are:

- The private zauberzeug-claude marketplace (PR-based; team-internal)
- LLM-only direct-install via the repo's root `.claude-plugin/marketplace.json`
- `pipx install game-of-cards` for traditional CLI users

None of these surface to a broader audience that browses Claude Code's
community marketplace. The community-listing card exists to close that
gap: a developer browsing community plugins should be able to discover
GoC, install it with one command, and have a usable plugin without
visiting any zauberzeug-owned URL.

The technical prerequisites for a marketplace-ready plugin are tracked
in their own cards:

- `bundle-goc-engine-inside-plugin-payload` (done) — plugin is now
  self-contained; install no longer requires `pipx install`.
- `add-readme-to-claude-code-plugin` (done 2026-05-08) — the
  marketplace-grade README.
- `align-skill-names-with-agile-vocabulary` (done 2026-05-08) — the
  skill names a reviewer and a fresh installer will see. Landing the
  rename *before* a broad-audience listing avoided forcing every
  early user through a migration.

This card tracks what those other cards don't: the manual submission
action.

## Outcome

Submitted via the form on 2026-05-09 and listed: GitHub issue #6
(2026-07-06), opened by the community-marketplace maintainers, refers
to game-of-cards as listed there. But the entry pins `4e4c5a10`
(2026-05-11), which predates the frontmatter fix `2f1ba0a5`, so the
listed build fails `claude plugin validate`. It has not followed any
release since; GitHub issue #8 tracks the lag. The card closed on
2026-10-22. Unfreezing the pin, the fresh-machine smoke and the
install-docs update continue in
[community-marketplace-pin-is-frozen-on-a-commit-that-fails-plugin-validation](../community-marketplace-pin-is-frozen-on-a-commit-that-fails-plugin-validation/).

## Why human_gate=decision (while open)

The submission itself is a user action — Rodja decides on the channel
(PR vs form) at submission time, opens it, and shepherds the review.
An autonomous agent should not file a PR to an Anthropic-owned
repository on the user's behalf. The card sits in the decision queue
until Rodja claims it explicitly.

## Out of scope

- The technical packaging work that the prereq cards already cover.
- Listing in the curated `claude-plugins-official` directory — that's
  a separate, heavier-review channel. If pursued, it should get its
  own card. The community marketplace is a strictly easier gate; do
  it first, learn from the review, then decide whether the official
  directory is worth the additional cost.
- Cross-runtime listings (Codex, OpenCode). Those ride on the
  respective `publish-codex-plugin` / `publish-openclaw-plugin`
  cards, not here.

## Cross-references

- `publish-claude-code-plugin` (done) — explicitly deferred this
  submission as option A in its decision section ("pursue
  Anthropic-official marketplace later"); this card is that
  deferred half.
- `add-readme-to-claude-code-plugin` (done 2026-05-08) — hard
  prereq.
- `align-skill-names-with-agile-vocabulary` (done 2026-05-08) — hard
  prereq (transitively, via the README), now satisfied.

## Notes

- Capture the fresh-machine smoke test as a written reproduction
  (steps + observed output). The submission reviewer is more likely
  to accept a plugin whose first-run experience has been demonstrated
  end-to-end on a clean environment than one that has only been
  tested on the maintainer's dev box.

## Decisions (2026-05-08, Rodja)

- **Submission channel: form at `clau.de/plugin-directory-submission`.**
  Verified at decision time: `anthropics/claude-plugins-community` is
  a read-only mirror; its README explicitly directs submitters to the
  form. The form feeds both community and (separately) the official
  marketplace — community-first is the lighter gate as already
  recommended in the body.
- **Version: stay pre-1.0 (currently 0.0.6).** Pre-1.0 is acceptable
  for the community marketplace; deferring the 1.0.0 stake-in-the-
  ground until after the listing has been live for a stretch and the
  audience has surfaced the rough edges.
- **Dry-run posture before submitting:** Trigger
  `release.yml` via `workflow_dispatch` with `dry_run=true` to confirm
  build + Path A/B smoke against current main; then manually smoke the
  actual marketplace install path on a clean profile (`/plugin
  marketplace add zauberzeug/game-of-cards` → `/plugin install` →
  prompt → card created), since the marketplace path is interactive-
  only and not headlessly testable in CI.

## Decision

*Resolved 2026-10-22T05:14:48Z:* Close: the listing exists; move the re-pin, the fresh-machine smoke and the docs update into a follow-up card

*Reasoning:* The maintainer decided in a human session on 2026-10-22; GitHub issue #6 from the community-marketplace maintainers confirms game-of-cards is listed, but the entry is frozen on 4e4c5a1, so the remaining work waits on a re-pin rather than on acceptance


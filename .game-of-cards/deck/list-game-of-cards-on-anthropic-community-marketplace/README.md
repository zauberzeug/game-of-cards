---
title: list-game-of-cards-on-anthropic-community-marketplace
summary: "Submit the Game of Cards Claude Code plugin to Anthropic's community marketplace (`anthropics/claude-plugins-community` or the equivalent submission form at `clau.de/plugin-directory-submission`) so a broader audience discovers it without first finding the zauberzeug GitHub repo. The technical work that produces a marketplace-ready plugin lives in other cards (bundle, README, skill renames); this card tracks the manual submission action itself — the PR or form submission Rodja makes, the review back-and-forth, and the post-merge documentation update."
status: open
stage: null
contribution: high
created: 2026-05-08
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - add-readme-to-claude-code-plugin
tags: [story, infra, documentation]
definition_of_done: |
  - [ ] All hard prereqs closed: `add-readme-to-claude-code-plugin` (whose own prereqs `bundle-goc-engine-inside-plugin-payload` and `align-skill-names-with-agile-vocabulary` are both done; awaits Rodja's marketplace-grade sign-off on the rendered README)
  - [ ] Decision recorded on submission channel: PR to `anthropics/claude-code-plugins` (or current canonical name) vs. form at `clau.de/plugin-directory-submission` vs. both. Capture the URL and current submission policy at decision time, since Anthropic's process may change between when the card was filed and when it's worked.
  - [ ] Fresh-machine smoke test passes: a clean environment with no prior `game-of-cards` install runs `/plugin marketplace add` (community marketplace) → `/plugin install game-of-cards@…` → prompts agent → agent creates a card. Zero global package installs required. Captured as a screen recording or written reproduction so the submission PR can link to it.
  - [ ] Version bumped intentionally if appropriate. Pre-1.0 (`0.0.x`) is acceptable for community marketplace; document the choice. If 1.0.0 is the chosen stake-in-the-ground, bump pyproject.toml + plugin.json + marketplace.json in lockstep (the existing CI tripwire enforces this).
  - [ ] Submission opened (PR or form). Card transitions to `active` at this point; the worker field captures the URL of the submission.
  - [ ] Submission accepted / merged. Card transitions to `done`.
  - [ ] Post-merge documentation updated: README install path, `llms.txt`, `CLAUDE_GOC.md` template, and homepage all mention the community marketplace as the canonical install path. The existing zauberzeug-claude private marketplace and direct-install fallback remain documented as alternatives.
  - [ ] `uv run goc validate` passes
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
- `add-readme-to-claude-code-plugin` (active, gate=session) — the
  marketplace-grade README; text written, awaiting Rodja's sign-off.
- `align-skill-names-with-agile-vocabulary` (done 2026-05-08) — the
  skill names a reviewer and a fresh installer will see. Landing the
  rename *before* a broad-audience listing avoided forcing every
  early user through a migration.

This card tracks what those other cards don't: the manual submission
action.

## Why human_gate=decision

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
- `add-readme-to-claude-code-plugin` (active, gate=session) — hard
  prereq; text written, awaits Rodja's sign-off.
- `align-skill-names-with-agile-vocabulary` (done 2026-05-08) — hard
  prereq (transitively, via the README), now satisfied.

## Notes

- At submission time, verify Anthropic's current submission policy
  and the canonical repo name. The README card body references both
  `anthropics/claude-plugins-community` and
  `clau.de/plugin-directory-submission` — the policy or naming may
  have evolved between card creation and pickup.
- Capture the fresh-machine smoke test as a written reproduction
  (steps + observed output). The submission reviewer is more likely
  to accept a plugin whose first-run experience has been demonstrated
  end-to-end on a clean environment than one that has only been
  tested on the maintainer's dev box.

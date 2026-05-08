---
title: add-readme-to-claude-code-plugin
summary: "Add `claude-plugin/README.md` so the plugin payload carries its own marketplace-grade documentation. Required surface for the eventual submission to the Anthropic community plugin directory; today's repo-level `README.md` targets a different audience and is not what the directory will display."
status: active
stage: null
contribution: low
created: 2026-05-08
closed_at: null
human_gate: none
advances: []
advanced_by:
  - bundle-goc-engine-inside-plugin-payload
tags: [story, infra]
definition_of_done: |
  - [ ] Plugin is self-contained — installing the plugin is the only opt-in step; no separate `pipx install game-of-cards` / `pip install game-of-cards` is required for `goc` to be callable from skills. Depends on `bundle-goc-engine-inside-plugin-payload`
  - [ ] `claude-plugin/README.md` exists and renders cleanly on GitHub
  - [ ] README states what the plugin provides (current GoC skill set + hooks, with counts that match the deck at close-time)
  - [ ] README documents the install path live at close-time (community marketplace `@claude-community` once listed, otherwise the existing `zauberzeug/game-of-cards` direct path)
  - [ ] README explains the first-run experience: plugin install + one prompt; **no** instructions to install a separate PyPI package for normal use
  - [ ] README links to the project homepage (game-of-cards.com), the upstream repo, and the MIT license
  - [ ] Rodja reads the rendered text and signs off before close
  - [ ] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Add a README to the Claude Code plugin payload

## Why

The plugin payload at `claude-plugin/` has no README of its own. Browsers
arriving at the plugin from the future Anthropic community marketplace
listing (`anthropics/claude-plugins-community`) will see only the
description field from `plugin.json`, plus whatever Anthropic decides to
display. The repo-level `README.md` exists but targets a different
audience — humans evaluating the GoC methodology, not plugin browsers
trying to figure out what they're installing.

This card adds the missing surface so that:

- The plugin payload can stand on its own when copied into the marketplace cache
- A future community-directory submission has the documentation prerequisite covered
- Direct-install users (`/plugin marketplace add zauberzeug/game-of-cards`)
  who land in the plugin folder via the GitHub URL get a useful first read

## Scope

In:
- A single new file at `claude-plugin/README.md`
- Written *once* against the self-contained plugin shape (no separate
  PyPI install), not against today's CLI-prerequisite shape

Out:
- The actual submission to `clau.de/plugin-directory-submission` — that's a
  separate user action, intentionally not tracked here
- Any change to the repo-level `README.md` (covered by
  `redesign-readme-as-llm-first-marketing-page`)
- Bumping to 1.0.0 — stay pre-1.0 for now; project is still early

## Depends on

The README cannot be written until the plugin is self-contained, because
the install story it documents is exactly what changes when bundling
lands. Drafting it against today's `pipx install game-of-cards`
prerequisite would produce text that has to be rewritten the day
`bundle-goc-engine-inside-plugin-payload` closes — wasted churn and a
window of marketplace-visible documentation drift in between.

Hard dependency:

- `bundle-goc-engine-inside-plugin-payload` (open, session-gated) —
  eliminate the external CLI install so the plugin works standalone
  from a single `/plugin install`

## Background context

Submission to the official curated directory (`claude-plugins-official`)
is downstream of, and blocked by, several existing cards in addition to
the one above:

- The skill-rename family (`align-skill-names-with-agile-vocabulary`,
  `rename-bootstrap-to-kickoff-as-onboarding-dialog`, …) — surface text
  that any reviewer will see, and that this README will have to name
  by their final names
- `redesign-readme-as-llm-first-marketing-page` and
  `build-game-of-cards-project-website` — the upstream-repo and
  homepage surfaces a reviewer follows from the plugin description

Those are not blockers for *this* card (the plugin README can land
before they do), but they are blockers for the broader official-listing
goal that this README is one step toward.

## Notes

- Two locked-step files already pin the plugin metadata
  (`claude-plugin/.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`); the README should not duplicate the
  description verbatim — it should expand on it.
- Per the byte-for-byte tripwire in `.github/workflows/ci.yml`, anything
  added under `claude-plugin/` that has a counterpart under
  `goc/templates/` must match. A README at the plugin root is *not* one
  of the byte-locked paths (only `claude-plugin/skills/` and
  `claude-plugin/hooks/deck_*.py` are), so this file lives only at
  `claude-plugin/README.md` and has no template counterpart.

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
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] `claude-plugin/README.md` exists and renders cleanly on GitHub
  - [ ] README states what the plugin provides (the 12 GoC skills + 3 hooks)
  - [ ] README documents the `goc` CLI prerequisite (`pip install game-of-cards` / `pipx install game-of-cards`) up front, since the plugin is a thin runtime wrapper around the CLI
  - [ ] README documents the install path users follow today (`zauberzeug/game-of-cards` marketplace), and is forward-compatible with the future community-marketplace listing without prematurely claiming it
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
- Wording that holds up regardless of which marketplace listing is live
  (today: only `zauberzeug/game-of-cards`; eventually: also
  `claude-plugins-community`)

Out:
- The actual submission to `clau.de/plugin-directory-submission` — that's a
  separate user action, intentionally not tracked here
- Any change to the repo-level `README.md` (covered by
  `redesign-readme-as-llm-first-marketing-page`)
- Bumping to 1.0.0 — Rodja's call: stay pre-1.0 for now, project is still
  early
- Bundling `goc` inside the plugin payload (covered by
  `bundle-goc-engine-inside-plugin-payload`); until that ships, the README
  must continue to document the CLI prerequisite

## Background context

Submission to the official curated directory (`claude-plugins-official`)
is downstream of, and blocked by, several existing cards:

- `bundle-goc-engine-inside-plugin-payload` — eliminate the external CLI
  dependency so the plugin works standalone after install
- The skill-rename family (`align-skill-names-with-agile-vocabulary`,
  `rename-bootstrap-to-kickoff-as-onboarding-dialog`, …) — surface text
  that any reviewer will see
- `redesign-readme-as-llm-first-marketing-page` and
  `build-game-of-cards-project-website` — the upstream-repo and homepage
  surfaces a reviewer follows from the plugin description

This card's only contract is the plugin-level README. Moving the rest is
out of scope.

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

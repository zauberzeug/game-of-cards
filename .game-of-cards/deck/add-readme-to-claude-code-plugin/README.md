---
title: add-readme-to-claude-code-plugin
summary: "Add `claude-plugin/README.md` so the plugin payload carries its own marketplace-grade documentation. Required surface for the eventual submission to the Anthropic community plugin directory; today's repo-level `README.md` targets a different audience and is not what the directory will display."
status: done
stage: null
contribution: low
created: 2026-05-08
closed_at: 2026-05-08
human_gate: none
advances:
  - list-game-of-cards-on-anthropic-community-marketplace
advanced_by:
  - bundle-goc-engine-inside-plugin-payload
  - align-skill-names-with-agile-vocabulary
tags: [story, infra]
definition_of_done: |
  - [x] Plugin is self-contained — installing the plugin is the only opt-in step; no separate `pipx install game-of-cards` / `pip install game-of-cards` is required for `goc` to be callable from skills. Depends on `bundle-goc-engine-inside-plugin-payload`
  - [x] `claude-plugin/README.md` exists and renders cleanly on GitHub
  - [x] README states what the plugin provides (current GoC skill set + hooks, with counts that match the deck at close-time)
  - [x] README documents the install path live at close-time (community marketplace `@claude-community` once listed, otherwise the existing `zauberzeug/game-of-cards` direct path)
  - [x] README explains the first-run experience: plugin install + one prompt; **no** instructions to install a separate PyPI package for normal use
  - [x] README links to the project homepage (game-of-cards.com), the upstream repo, and the MIT license
  - [x] Rodja reads the rendered text and signs off before close
  - [x] `uv run goc validate` passes
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

The README cannot be written until two things settle: the install
story it documents and the skill names it lists. Drafting against
either a soon-to-change install recipe or soon-to-change skill names
produces text that has to be rewritten when those upstream cards
close — wasted churn and a window of marketplace-visible
documentation drift in between.

Hard dependencies (both satisfied):

- `bundle-goc-engine-inside-plugin-payload` (done) — eliminated the
  external CLI install so the plugin works standalone from a single
  `/plugin install`. Closed 2026-05-08.
- `align-skill-names-with-agile-vocabulary` (done) — the
  skill names the README lists in the "what's in the plugin"
  section. Promoted from soft to hard prereq because the community
  marketplace is a *broad* audience surface — every additional user
  acquired before a rename is a user who later has to migrate. Better
  to land the rename first and ship clean names than to ship,
  acquire users, and then force a migration on everyone. Closed 2026-05-08.

## Background context

The skill-rename dependency above used to be listed here as a soft
blocker for the *official curated* directory only. It has been
promoted to a hard prereq for the community marketplace listing too,
on the grounds that broad-audience releases warrant breaking-change
conservatism: bigger blast radius means the cost of a post-release
rename grows faster than the cost of waiting.

Other items relevant to the broader official-listing goal (already
done):

- `redesign-readme-as-llm-first-marketing-page` (done) — the
  upstream-repo surface a reviewer follows from the plugin description
- `build-game-of-cards-project-website` (done) — the homepage surface
  a reviewer follows from the plugin description

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

## Sign-off required

`claude-plugin/README.md` has been written and committed. Before this
card can close, Rodja needs to read the rendered text and confirm it's
ready for marketplace-grade use. Gate is raised to `session` pending that
review.

To close after sign-off:

```bash
goc decide add-readme-to-claude-code-plugin --decision "approved" --because "Rodja: text is marketplace-ready"
goc done add-readme-to-claude-code-plugin
```

## Decision

*Resolved 2026-05-08:* approved

*Reasoning:* Rodja: text is marketplace-ready

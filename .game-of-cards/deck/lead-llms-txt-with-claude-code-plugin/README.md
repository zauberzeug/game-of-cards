---
title: lead-llms-txt-with-claude-code-plugin
summary: Reorder site/llms.txt so the Claude Code plugin install is the headline path and the Python uv/pipx CLI install becomes the secondary path for non-Claude-Code agent runtimes and CI.
status: open
stage: null
contribution: medium
created: 2026-05-09
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [ ] `site/llms.txt` reorders Install sections so the Claude Code plugin install is first under a section labelled for Claude Code, and the Python `uv tool install` / `pipx install` recipe is second under a section labelled for other agent runtimes / CI.
  - [ ] The marketplace-update warning currently at lines 37–50 (the "Updating after a new release" block, the explanation that `/plugin install` reuses a stale local clone, and the `marketplace remove` round-trip fallback) is preserved verbatim under the new Claude Code section.
  - [ ] The `goc install` repo-init step appears in the Python / CI section so non-plugin users still see how to bootstrap a repo.
  - [ ] No other content in `site/llms.txt` is dropped (the headline blurb, "Key concepts", "Daily commands", and "More" link list remain).
  - [ ] `uv run goc validate` passes after the edit.
---

# lead-llms-txt-with-claude-code-plugin

## Why this card exists

`site/llms.txt` is the project's machine-readable install/usage manifest aimed
at LLM consumers (per the [llms.txt convention](https://llmstxt.org)). Its
audience is overwhelmingly agents running inside Claude Code, Codex, Cursor,
and similar runtimes. As of 2026-05-09 the file leads with `uv tool install
game-of-cards` at lines 11–14 under "## Install" and presents the plugin as a
"## Lean alternative for Claude Code" subsection at line 26+. That ordering
teaches downstream LLMs to recommend the heavier path (which writes files into
the consuming repo) before the lighter, no-checked-in-files plugin path that
fits the dominant audience.

This card is a pure documentation reordering — neither install path changes,
neither is removed, and the underlying CLI is the same in both cases. The
plugin wraps the same `goc` engine via `claude-plugin/bin/goc`. The change is
purely about which path the file presents *first*.

## Decision recorded (from the chat that filed this card)

Framing chosen: **Plugin first, Python second** (rather than peer side-by-side
or preserving the current ordering). The Python CLI is presented as the path
for non-Claude-Code agent runtimes and CI environments without plugin support,
not as a fallback or "alternative."

## Target structure (illustrative, not normative)

```
## Install (Claude Code)

/plugin marketplace add zauberzeug/game-of-cards
/plugin install game-of-cards@game-of-cards

(then the marketplace-update warning block, preserved verbatim from
current lines 37–50)

## Install (other agent runtimes / CI)

uv tool install game-of-cards   # or: pipx install game-of-cards

Initialize a repo:

goc install
```

The exact heading wording is at the implementer's discretion provided it
makes the audience split obvious to a cold LLM reader. Keep the one-line
hook before each command block so a downstream LLM can decide which to
recommend without parsing prose.

## Out of scope

- Changing the install paths themselves, removing either path, or rewriting
  CLI commands.
- Editing other docs (the README, the `site/` MkDocs pages, AGENTS.md, or
  CLAUDE.md). If those docs have the same ordering problem, file separate
  cards — keep this one focused on `site/llms.txt`.
- Rewriting the headline blurb, "Key concepts", "Daily commands", or "More"
  link list in `site/llms.txt`. Those sections are downstream of the install
  framing and should not move.

## Sequencing

Two cards are active when this card is filed (per the SessionStart reminder
on 2026-05-09):

- support-external-game-of-cards-state-location
- surface-active-cards-in-board

Per the GoC "resume or close before starting new work" guard, this card
stays `open` until those close. It is gate `none` so any agent can pull it
once the active queue clears.

---
title: add-openclaw-coverage-to-readme-personas-and-website
summary: |-
  The OpenClaw plugin landed but the public-facing materials still
  describe GoC as Claude-Code-only. README.md, ABOUT.md, PERSONAS.md,
  goc.md, and site/index.html all have zero OpenClaw mentions — they
  closed before the plugin shipped. Only site/llms.txt was refreshed
  (`add-openclaw-install-section-to-llms-txt`, done 2026-05-09).
  Bring the rest of the front-door materials up to date.
status: done
stage: null
contribution: medium
created: 2026-05-10
closed_at: 2026-05-11T03:56:32Z
human_gate: none
advances: []
advanced_by: []
tags: [documentation, story]
definition_of_done: |
  - [x] decision recorded below for whether OpenClaw introduces a new
        persona or widens existing ones
  - [x] README.md mentions OpenClaw in install / harness coverage
        (sibling to Claude Code), with the same depth treatment llms.txt
        gives
  - [x] PERSONAS.md updated per the persona decision (either a new
        persona section or amended workflow recommendations on existing
        personas)
  - [x] ABOUT.md updated to reference OpenClaw alongside its existing
        OpenCode mention (current state: only OpenCode is named, line 80)
  - [x] goc.md adds an OpenClaw plugin section sibling to its existing
        Claude Code plugin section (line 83+)
  - [x] site/index.html surfaces OpenClaw as a delivery channel
        equivalent in standing to the Claude Code plugin
  - [x] cross-links to the canonical OpenClaw entry point
        (https://openclaw.ai and the ClawHub install command) wherever
        introduced
  - [x] no regression in existing Claude Code / pipx coverage; this
        card adds, never removes
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# add-openclaw-coverage-to-readme-personas-and-website

## What's missing

Audit performed 2026-05-10 against `main`. OpenClaw mentions per file:

| File | OpenClaw mentions | Last touched by |
|---|---|---|
| `site/llms.txt` | Yes — full `## Install (OpenClaw)` section, lines 39-53 | `add-openclaw-install-section-to-llms-txt` (done 2026-05-09) |
| `README.md` | None | `redesign-readme-as-llm-first-marketing-page` (done before plugin) |
| `PERSONAS.md` | None | `define-personas-and-use-cases-for-game-of-cards` (done 2026-05-08, before plugin) |
| `ABOUT.md` | None (mentions only OpenCode at line 80) | various, none post-plugin |
| `goc.md` | None | predates plugin |
| `site/index.html` | None | `build-game-of-cards-project-website` (done 2026-05-05, before plugin) |

So five of the six front-door files are stale relative to the OpenClaw
delivery channel.

## Why it matters

The OpenClaw plugin is now a first-class delivery channel — bundled
engine, single host prerequisite (`python3` ≥ 3.10), available via
ClawHub and npm. New users who arrive via OpenClaw read README and the
website to confirm the project's positioning. If those documents do not
acknowledge OpenClaw, the message lands as "this is a Claude Code
project that we tolerated installing in OpenClaw" rather than "first-class
support across both runtimes." That undersells the plugin and may push
OpenClaw users toward `pipx install game-of-cards` (the generic recipe
in llms.txt) when the plugin is the recommended path.

The personas doc is the most consequential to think through. The
existing persona seeds (per `define-personas-and-use-cases-for-game-of-cards`)
are: vibe-coder; solo dev linear-planner; classical team strict-commit;
agent-runtime non-code; multi-human + multi-AI on shared codebase. None
of those personas is *defined by* their host runtime. So the decision is
whether OpenClaw introduces a genuinely new persona shape or just
widens the install-path coverage on existing ones.

## Decision

*Resolved 2026-05-10:* Q1: Add a single 'OpenClaw user' persona section in PERSONAS.md. Q2: Add a sibling 'Install (OpenClaw)' section in README, parallel to the existing Claude Code install section.

*Reasoning:* Q1: the registered-tool model and ClawHub distribution are distinct enough to deserve a named user. Q2: OpenClaw deserves equal billing on the front door.
## Out of scope

- New OpenClaw-host-specific skills or hooks. Those are tracked under
  `provide-openclaw-plugin-for-skills-and-hooks` (active) and its
  follow-ups.
- OpenClaw plugin's own README (separate card:
  `add-readme-to-claude-code-plugin` is the pattern for Claude Code; an
  equivalent OpenClaw-plugin README card would be its own filing).
- Renaming "agent-runtime / CI" persona — Q1 explicitly recommends
  not splitting it.

## Notes

- `provide-openclaw-plugin-for-skills-and-hooks` is currently `active`
  with a pending session gate. This card should not start until that
  one closes, otherwise the documentation will reference plugin
  affordances that may still shift.
- Worth re-reading `redesign-readme-as-llm-first-marketing-page` (done)
  to understand the README's voice and tone before drafting OpenClaw
  copy.
- Cross-link target: <https://openclaw.ai> for the runtime; the
  ClawHub install command (`openclaw skills install game-of-cards`)
  for the install path.

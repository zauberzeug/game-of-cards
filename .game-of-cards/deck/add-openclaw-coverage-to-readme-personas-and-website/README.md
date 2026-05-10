---
title: add-openclaw-coverage-to-readme-personas-and-website
summary: |
  The OpenClaw plugin landed but the public-facing materials still
  describe GoC as Claude-Code-only. README.md, ABOUT.md, PERSONAS.md,
  goc.md, and site/index.html all have zero OpenClaw mentions — they
  closed before the plugin shipped. Only site/llms.txt was refreshed
  (`add-openclaw-install-section-to-llms-txt`, done 2026-05-09).
  Bring the rest of the front-door materials up to date.
status: open
stage: null
contribution: medium
created: 2026-05-10
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [documentation, story]
definition_of_done: |
  - [ ] decision recorded below for whether OpenClaw introduces a new
        persona or widens existing ones
  - [ ] README.md mentions OpenClaw in install / harness coverage
        (sibling to Claude Code), with the same depth treatment llms.txt
        gives
  - [ ] PERSONAS.md updated per the persona decision (either a new
        persona section or amended workflow recommendations on existing
        personas)
  - [ ] ABOUT.md updated to reference OpenClaw alongside its existing
        OpenCode mention (current state: only OpenCode is named, line 80)
  - [ ] goc.md adds an OpenClaw plugin section sibling to its existing
        Claude Code plugin section (line 83+)
  - [ ] site/index.html surfaces OpenClaw as a delivery channel
        equivalent in standing to the Claude Code plugin
  - [ ] cross-links to the canonical OpenClaw entry point
        (https://openclaw.ai and the ClawHub install command) wherever
        introduced
  - [ ] no regression in existing Claude Code / pipx coverage; this
        card adds, never removes
  - [ ] `uv run goc validate` passes
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

## Decision required

### Q1 — does OpenClaw introduce a new persona?

#### Option A — no new persona; widen install-path coverage on existing ones

Existing personas keep their definitions; their "workflow recommendation"
column gets an OpenClaw install path alongside Claude Code where
applicable. Anti-personas list stays identical.

- **Pro**: minimal scope; persona shape stays driven by workflow, not
  runtime.
- **Con**: misses the chance to call out OpenClaw-specific affordances
  (lobster theme, ClawHub registry, registered-tool model) if any
  produce a meaningfully different user.

#### Option B — add an "OpenClaw user" persona

New persona section describing someone who lives in the OpenClaw
runtime (personal AI assistant, Node-based, ClawHub-distributed) and
adopts GoC as their methodology layer.

- **Pro**: matches the way personas have been named ("vibe-coder",
  "classical team") — by their primary working environment.
- **Con**: encourages the slippery slope where every new host runtime
  spawns a new persona; the persona doc bloats.

#### Option C — split the agent-runtime persona by host

The existing "agent-runtime / CI" persona already covers AI-driven
work; split it into "Claude Code agent-runtime" and "OpenClaw
agent-runtime" with their own install-path notes.

- **Pro**: preserves the runtime-distinct trade-offs (host-specific
  hooks, tool-registration shape, plugin distribution) without a
  net-new persona.
- **Con**: artificial split; agent-runtime concerns are mostly the
  same regardless of host.

**Recommendation**: Option A. Personas should track *workflow shape*,
not *host*. OpenClaw is an install-path change, not a workflow-shape
change. Reserve a new persona for genuinely new shapes (e.g., a
non-engineer office worker using GoC for a knowledge-work backlog).

### Q2 — what depth of OpenClaw treatment in README?

#### Option I — sibling install section, same depth as Claude Code

Mirror `site/llms.txt` exactly: a `## Install (OpenClaw)` section
sibling to the existing `## Install (Claude Code)` section. Three to
five lines: ClawHub install command, npm package name, the
registered-tool note, the python3 prerequisite.

- **Pro**: consistent with llms.txt; LLMs that have read llms.txt
  will recognize the same shape on the README.
- **Con**: README might already be opinionated about Claude Code as
  the recommended runtime — adding a peer section requires checking
  README's current install-recommendation prose for inconsistencies.

#### Option II — short callout + link to llms.txt section

A two-line "GoC also ships as an OpenClaw plugin — see [llms.txt]"
callout near the install section.

- **Pro**: zero risk of duplication drift between README and llms.txt.
- **Con**: undersells OpenClaw as a delivery channel; reads as
  afterthought.

**Recommendation**: Option I. README is the front door for evaluators;
the OpenClaw plugin deserves equal billing.

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

---
title: provide-openclaw-plugin-for-skills-and-hooks
summary: "Replace the blocked OpenClaw harness direction with a later OpenClaw plugin/runtime package for Game of Cards skills and hooks. This supersedes `install-openclaw-harness` and should wait until the Claude/Codex plugin pattern is clear or an OpenClaw consumer appears."
status: open
stage: null
contribution: high
created: 2026-05-05
closed_at: null
human_gate: none
advances:
  - support-external-game-of-cards-state-location
  - publish-openclaw-plugin
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] `install-openclaw-harness` is marked superseded with a log entry pointing here
  - [x] OpenClaw plugin/runtime extension format confirmed from upstream docs (`SKILL.md` directories with YAML frontmatter; five-tier precedence; ClawHub at <https://clawhub.ai>; consumer install verb `openclaw skills install`) — see "## What is OpenClaw" body section
  - [ ] Plugin supplies GoC skills as `SKILL.md` directories at the **workspace** precedence tier
  - [ ] Plugin shells out to host-installed `goc` CLI; consumer-side prerequisite is `pipx install game-of-cards` (no Python runtime vendored in the npm package)
  - [ ] Plugin delegates durable state to `.game-of-cards` and the `goc` CLI
  - [ ] OpenClaw hook/event surface investigated and the SessionStart/UserPromptSubmit/Stop equivalence (or gap) documented in this card's log
  - [ ] Plugin published on ClawHub (<https://clawhub.ai>) so consumers can `openclaw skills install <id>`
  - [ ] Plugin published as the npm package `game-of-cards` (name verified available on the npm registry 2026-05-09; first publish claims it)
  - [ ] Docs list OpenClaw plugin support separately from repo-local harness installation
  - [ ] Smoke test confirms OpenClaw can discover/use the plugin in a fresh repo
  - [ ] `uv run goc validate` passes
---

# Provide an OpenClaw plugin for skills and hooks

## What is OpenClaw

OpenClaw is an open-source personal AI assistant that runs on the user's own devices and answers across messaging channels. **It is a distinct product from OpenCode (sst/opencode)** — do not assume the deck's "OpenClaw" is a typo for "OpenCode"; they are unrelated runtimes with separate cards.

Identity anchors (verified 2026-05-09 against upstream sources):

- Repository: <https://github.com/openclaw/openclaw> — tagline *"Your own personal AI assistant. Any OS. Any Platform. The lobster way. 🦞"*
- Site: <https://openclaw.ai>; docs: <https://docs.openclaw.ai>
- Runtime: Node 24 recommended, Node 22.16+ minimum
- Install: `npm install -g openclaw@latest` (pnpm/bun supported)
- Setup verb: `openclaw onboard`
- Skills format: each skill is a directory containing `SKILL.md` with YAML frontmatter (`name`, `description` required); see <https://docs.openclaw.ai/tools/skills>
- Skill precedence (highest first): workspace → project agent → personal agent → managed/local → bundled → extra skill folders
- Public skills registry: ClawHub at <https://clawhub.ai>; consumer-side install verb is `openclaw skills install`

OpenCode, by contrast, reads `.claude/skills/` natively (see `ABOUT.md`) and gets GoC for free via the Claude harness path; that is why there is no separate OpenCode plugin card.

## Why

The previous OpenClaw work was framed as another `goc install --agents openclaw` repo-local harness. The clarified direction is plugin-first: Claude Code and Codex plugins first, then OpenClaw later. This card replaces the blocked harness card.

## Decisions recorded

Three architectural decisions resolved 2026-05-09; gate lowered from `session` to `none`.

- **Bundling**: shell out to host-installed `goc` (consumers run `pipx install game-of-cards` first). Why: smallest plugin to ship and matches the Claude plugin's pre-bundling state; vendoring a Python runtime inside an npm package is unusually complex; the friction of a one-time `pipx install` is acceptable "for now" and the decision is revisitable if it proves too high. The Claude plugin's vendored-engine pattern (`bundle-goc-engine-inside-plugin-payload`) was deliberately not adopted here — different host, different tradeoffs. The `advanced_by` edge to that card was removed accordingly.
- **Skill tier**: `workspace`. Why: GoC is inherently per-repo (each repo has its own `.game-of-cards/deck`), so workspace-scoped skills match the model. `bundled` would imply universal skills with no specific deck to operate against; `managed/local` is closer but workspace is the cleanest semantic match for "skills that come alive when you `cd` into a GoC repo."
- **Distribution**: publish on ClawHub **and** npm. Why: ClawHub is the OpenClaw-native install path; npm both serves as an alternative install path for non-ClawHub consumers and claims the `game-of-cards` name on the registry (verified available 2026-05-09 — `goc` is squatted with a placeholder, but `game-of-cards` is clean for first-publish, matching the PyPI name).

## Implementation anchors (still open for the executor)

- **Hook surface**: investigate OpenClaw's session/lifecycle events (`docs.openclaw.ai/concepts/session`, `docs.openclaw.ai/concepts/agent`, plus the `/new`/`/reset`/`/compact` chat commands) and determine which carry GoC's SessionStart / UserPromptSubmit / Stop semantics. If hooks don't translate, document the gap in this card's log rather than ship a half-working analogue. This is research that produces a documented finding, not a decision the human needs to weigh in on.
- **Plugin scaffold**: a thin npm package whose `SKILL.md` files invoke `goc <verb>` directly (since `goc` is host-installed via pipx). Reference shape: the existing Claude plugin's skill bodies under `claude-plugin/skills/` — most logic stays in `goc`, the plugin is mostly format-translation glue.
- **Smoke test target**: a fresh repo with `pipx install game-of-cards`, `npm install -g openclaw`, plugin installed via ClawHub, then exercise `goc new`/`goc done` through OpenClaw.

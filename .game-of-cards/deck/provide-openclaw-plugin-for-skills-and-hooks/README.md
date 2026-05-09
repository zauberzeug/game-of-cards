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
advanced_by:
  - bundle-goc-engine-inside-plugin-payload
tags: [story, infra]
definition_of_done: |
  - [x] `install-openclaw-harness` is marked superseded with a log entry pointing here
  - [x] OpenClaw plugin/runtime extension format confirmed from upstream docs (`SKILL.md` directories with YAML frontmatter; five-tier precedence; ClawHub at <https://clawhub.ai>; consumer install verb `openclaw skills install`) — see "## What is OpenClaw" body section
  - [ ] Plugin supplies GoC skills as `SKILL.md` directories at the **workspace** precedence tier
  - [ ] Plugin vendors the goc engine inside the npm payload (parallel to `claude-plugin/goc/`) with a `bin/goc` wrapper that invokes `uv run --project ${OPENCLAW_PLUGIN_ROOT}` — symmetric to the Claude plugin pattern from `bundle-goc-engine-inside-plugin-payload`
  - [ ] Consumer-side prerequisite is `python3` + `uv` on PATH (matches Claude plugin); no separate `pipx install game-of-cards` step required
  - [ ] OpenClaw plugin-bin PATH integration verified from upstream docs/source: confirm whether OpenClaw auto-prepends a plugin's `bin/` to skill-execution PATH (parallel to Claude Code), or whether a substitute resolution path (post-install symlink, absolute-path invocation in skills, etc.) is needed; outcome recorded in this card's log
  - [ ] Plugin delegates durable state to `.game-of-cards` and the `goc` CLI
  - [ ] OpenClaw hook/event surface investigated and the SessionStart/UserPromptSubmit/Stop equivalence (or gap) documented in this card's log
  - [ ] Plugin published on ClawHub (<https://clawhub.ai>) so consumers can `openclaw skills install <id>`
  - [ ] Plugin published as the npm package `game-of-cards` (name verified available on the npm registry 2026-05-09; first publish claims it)
  - [ ] Docs list OpenClaw plugin support separately from repo-local harness installation; document the `python3` + `uv` prerequisite explicitly
  - [ ] Smoke test confirms OpenClaw can discover/use the plugin in a fresh repo with no `pipx`-style fallback
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
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

Three architectural decisions resolved 2026-05-09; gate lowered from `session` to `none`. The bundling decision was pivoted later the same day after re-examining prerequisites.

- **Bundling** (pivoted 2026-05-09): vendor the goc engine inside the npm payload, **symmetric to the Claude plugin** (`bundle-goc-engine-inside-plugin-payload`). The plugin ships `goc/` source plus a `bin/goc` shell wrapper that resolves the package via `uv run --project ${OPENCLAW_PLUGIN_ROOT}`. Consumer-side prerequisite is `python3` + `uv` (same as the Claude plugin), not `pipx`.
  - Why pivoted: the original "shell out + `pipx install game-of-cards`" decision underestimated how rare `pipx` is on developer machines in 2026 relative to `uv`. If the user already needs a Python toolchain we don't ship, requiring `uv` (consistent with Claude) is lower friction than requiring `pipx` (a different less-fashionable tool). Symmetric architecture also simplifies the future `generate-plugin-payloads-from-templates-on-release` work — one templated emission instead of two divergent shapes.
  - The `advanced_by: bundle-goc-engine-inside-plugin-payload` edge was removed under the original decision, then **restored** under the pivot. The Claude plugin's vendored-engine + `bin/goc` wrapper is now the direct reference shape, not a contrast.
  - **Critical assumption flagged for verification during implementation**: OpenClaw must auto-prepend a plugin's `bin/` to the skill-execution PATH the way Claude Code does, OR provide an alternative path-resolution mechanism. If neither is available, the fallback is to invoke `goc` via an absolute path discovered at runtime in each `SKILL.md`. The DoD now contains an explicit research item to land this answer.
- **Skill tier**: `workspace`. Why: GoC is inherently per-repo (each repo has its own `.game-of-cards/deck`), so workspace-scoped skills match the model. `bundled` would imply universal skills with no specific deck to operate against; `managed/local` is closer but workspace is the cleanest semantic match for "skills that come alive when you `cd` into a GoC repo."
- **Distribution**: publish on ClawHub **and** npm. Why: ClawHub is the OpenClaw-native install path; npm both serves as an alternative install path for non-ClawHub consumers and claims the `game-of-cards` name on the registry (verified available 2026-05-09 — `goc` is squatted with a placeholder, but `game-of-cards` is clean for first-publish, matching the PyPI name).

## Implementation anchors (still open for the executor)

- **PATH integration spike** (the highest-leverage research): read OpenClaw's plugin/skill-execution docs and source to determine whether a plugin's `bin/` is auto-added to the shell PATH when its `SKILL.md` invokes commands. Three plausible outcomes: (a) it does — implementation proceeds as a near-clone of the Claude plugin shape; (b) it doesn't, but there's an install-time PATH-shim mechanism — adopt that; (c) it doesn't and there's no equivalent — fall back to absolute-path invocations in each `SKILL.md` (uglier but functional). Record the finding in this card's log before proceeding.
- **Hook surface**: investigate OpenClaw's session/lifecycle events (`docs.openclaw.ai/concepts/session`, `docs.openclaw.ai/concepts/agent`, plus the `/new`/`/reset`/`/compact` chat commands) and determine which carry GoC's SessionStart / UserPromptSubmit / Stop semantics. If hooks don't translate, document the gap in this card's log rather than ship a half-working analogue.
- **Plugin scaffold**: an npm package containing `goc/` (vendored Python source) + `bin/goc` (uv-run shell wrapper) + `SKILL.md` directories. Reference shape: `claude-plugin/` (mirror layout: `claude-plugin/goc/`, `claude-plugin/bin/goc`, `claude-plugin/skills/`).
- **Smoke test target**: a fresh repo with `python3` + `uv` + `npm install -g openclaw`, plugin installed via ClawHub, then exercise `goc new`/`goc done` through OpenClaw — no `pipx` step required.

## Decision required (2026-05-09)

Two blockers prevent autonomous completion:

1. **DoD is outdated**: Items 4 and 5 reference the old `uv run --project` wrapper pattern that was just removed in `plugin-wrapper-drops-uv`. The Claude plugin now uses `python3 -m goc.cli` directly (no uv). Decide: should the OpenClaw wrapper follow the same pattern (python3 only), or keep uv for the npm/Node context where uv is less common?

2. **External publishing requires human accounts**: DoD items 9 (ClawHub) and 10 (npm) require accounts and publishing rights that are not available to autonomous agents. These need human action regardless of the implementation decision.

Suggested next step: Rodja (or another human) resolves (1) above, then either delegates the implementation to the agent queue (gate → none) or executes the publish steps directly. The local implementation (SKILL.md directories, engine vendor, bin/goc wrapper) can be done autonomously once the wrapper pattern is confirmed.

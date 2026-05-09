---
title: provide-openclaw-plugin-for-skills-and-hooks
summary: "Replace the blocked OpenClaw harness direction with a later OpenClaw plugin/runtime package for Game of Cards skills and hooks. This supersedes `install-openclaw-harness` and should wait until the Claude/Codex plugin pattern is clear or an OpenClaw consumer appears."
status: open
stage: null
contribution: high
created: 2026-05-05
closed_at: null
human_gate: decision
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
  - [ ] Plugin vendors the goc engine inside the npm payload (parallel to `claude-plugin/goc/`) with a `bin/goc` wrapper that invokes `python3 -m goc.cli "$@"` directly — symmetric to the Claude plugin pattern from `bundle-goc-engine-inside-plugin-payload` and `plugin-wrapper-drops-uv`
  - [ ] Consumer-side prerequisite is `python3` (3.10+) on PATH (matches the Claude plugin after `plugin-wrapper-drops-uv`); no `uv` and no separate `pipx install game-of-cards` step required
  - [x] OpenClaw plugin-bin PATH integration verified from upstream docs/source: confirm whether OpenClaw auto-prepends a plugin's `bin/` to skill-execution PATH (parallel to Claude Code), or whether a substitute resolution path (post-install symlink, absolute-path invocation in skills, etc.) is needed; outcome recorded in this card's log
  - [ ] Plugin delegates durable state to `.game-of-cards` and the `goc` CLI
  - [x] OpenClaw hook/event surface investigated and the SessionStart/UserPromptSubmit/Stop equivalence (or gap) documented in this card's log
  - [ ] Plugin published on ClawHub (<https://clawhub.ai>) so consumers can `openclaw skills install <id>`
  - [ ] Plugin published as the npm package `game-of-cards` (name verified available on the npm registry 2026-05-09; first publish claims it)
  - [ ] Docs list OpenClaw plugin support separately from repo-local harness installation; document the `python3` (3.10+) prerequisite explicitly (no `uv` required)
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

- **Bundling** (pivoted twice; final 2026-05-09): vendor the goc engine inside the npm payload, **symmetric to the Claude plugin** (`bundle-goc-engine-inside-plugin-payload`). The plugin ships `goc/` source plus a `bin/goc` shell wrapper that invokes `python3 -m goc.cli "$@"` directly — no `uv`, no `--project`, no venv materialization.
  - First pivot (earlier 2026-05-09): rejected the "shell out + `pipx install game-of-cards`" plan in favor of "shell out + `uv run --project ${PLUGIN_ROOT}`", on the reasoning that `uv` is more common than `pipx` on dev machines.
  - Second pivot (later 2026-05-09): once `plugin-wrapper-drops-uv` landed (engine went pure-stdlib via `replace-pyyaml-with-vendored-parser` + `replace-click-with-argparse`), `uv` was no longer needed even as a venv provisioner. The Claude wrapper switched to plain `python3 -m goc.cli` and the OpenClaw wrapper now mirrors that exactly. Rationale: `python3` (3.10+) is broadly distributed; `uv` is opt-in tooling. Drops a runtime prerequisite for OpenClaw consumers at no implementation cost (the engine is already pure-stdlib).
  - The `advanced_by: bundle-goc-engine-inside-plugin-payload` edge stays — the Claude plugin's vendored-engine + `bin/goc` wrapper remains the direct reference shape.
  - **Critical assumption flagged for verification during implementation**: OpenClaw must auto-prepend a plugin's `bin/` to the skill-execution PATH the way Claude Code does, OR provide an alternative path-resolution mechanism. If neither is available, the fallback is to invoke `goc` via an absolute path discovered at runtime in each `SKILL.md`. The DoD contains an explicit research item to land this answer.
- **Skill tier**: `workspace`. Why: GoC is inherently per-repo (each repo has its own `.game-of-cards/deck`), so workspace-scoped skills match the model. `bundled` would imply universal skills with no specific deck to operate against; `managed/local` is closer but workspace is the cleanest semantic match for "skills that come alive when you `cd` into a GoC repo."
- **Distribution**: publish on ClawHub **and** npm. Why: ClawHub is the OpenClaw-native install path; npm both serves as an alternative install path for non-ClawHub consumers and claims the `game-of-cards` name on the registry (verified available 2026-05-09 — `goc` is squatted with a placeholder, but `game-of-cards` is clean for first-publish, matching the PyPI name).

## Implementation anchors (still open for the executor)

- **PATH integration spike** (the highest-leverage research): read OpenClaw's plugin/skill-execution docs and source to determine whether a plugin's `bin/` is auto-added to the shell PATH when its `SKILL.md` invokes commands. Three plausible outcomes: (a) it does — implementation proceeds as a near-clone of the Claude plugin shape; (b) it doesn't, but there's an install-time PATH-shim mechanism — adopt that; (c) it doesn't and there's no equivalent — fall back to absolute-path invocations in each `SKILL.md` (uglier but functional). Record the finding in this card's log before proceeding.
- **Hook surface**: investigate OpenClaw's session/lifecycle events (`docs.openclaw.ai/concepts/session`, `docs.openclaw.ai/concepts/agent`, plus the `/new`/`/reset`/`/compact` chat commands) and determine which carry GoC's SessionStart / UserPromptSubmit / Stop semantics. If hooks don't translate, document the gap in this card's log rather than ship a half-working analogue.
- **Plugin scaffold**: an npm package containing `goc/` (vendored Python source) + `bin/goc` (python3 shell wrapper, mirroring `claude-plugin/bin/goc` after `plugin-wrapper-drops-uv`) + `SKILL.md` directories. Reference shape: `claude-plugin/` (mirror layout: `claude-plugin/goc/`, `claude-plugin/bin/goc`, `claude-plugin/skills/`).
- **Smoke test target**: a fresh repo with `python3` (3.10+) + `npm install -g openclaw`, plugin installed via ClawHub, then exercise `goc new`/`goc done` through OpenClaw — no `uv` and no `pipx` step required.

## Decision required (2026-05-09, second pass — PATH-integration spike result)

The PATH-integration spike (DoD item 6) and hook-surface spike (DoD item 8) ran against upstream OpenClaw docs. Full findings are in `log.md`. **The first spike's result invalidates part of the wrapper-pattern decision below**: OpenClaw has no `bin` field in its plugin manifest, no `registerBin`/`providePathEntry` SDK API, and no documented mechanism for adding plugin executables to the skill-execution PATH. Plugin CLI commands register via `api.registerCli()` from TypeScript, which makes them OpenClaw-native verbs (`openclaw <verb>`) rather than entries on the user's shell PATH. So the "drop a `bin/goc` wrapper, let the runtime auto-prepend" model from `claude-plugin/` does not transfer.

Three real options remain:

- **α — Tool wrapper.** Register goc as an OpenClaw tool via `api.registerTool('goc', { params: {...}, async execute(...) { /* shell out to bundled python3 -m goc.cli */ } })`. Skills instruct the model to use the registered tool rather than bash-exec'ing `goc` directly. Plugin is self-contained; no PATH magic. Cost: the ~13 SKILL.md bodies fork from the Claude versions (different invocation style), and the plugin entry is real TypeScript code, not just a vendored-payload mirror.
- **β — Bring your own goc.** Plugin only ships SKILL.md + hook registrations. No bundled engine. Consumer runs `pipx install game-of-cards` (or system equivalent) so `goc` is on the OS PATH. Skills are byte-identical to Claude versions. Cost: reintroduces the `pipx` step we just removed for the Claude path; consumer experience is asymmetric.
- **γ — Hybrid.** Bundle engine + register tool (idiomatic in-OpenClaw flow), AND document `pipx install game-of-cards` as a fallback for consumers who want shell access. Cost: two code paths, doubled docs surface.

**Recommendation: β.** Lowest implementation cost; byte-identical skill content; the `pipx` friction is asymmetric only with the auto-PATH-prepend feature OpenClaw doesn't have. The "no pipx" promise on the Claude side rested on a feature unique to Claude Code — it was never a portable promise. Accepting one extra consumer install command on the OpenClaw side seems the right balance against forking 13 skill bodies (α) or shipping two stacks (γ).

That said, **α has a real architectural payoff**: it makes GoC a "real" OpenClaw plugin (registered tool, programmatic hooks) rather than a thin SKILL.md drop. If GoC is positioned as a flagship OpenClaw plugin rather than a courtesy port, α earns its weight.

If **β** chosen: next pull-card iteration scaffolds an npm package listing SKILL.md directories under workspace tier and a thin TypeScript shim mapping the three current hooks to OpenClaw's `session_start` / `before_agent_run` / `agent_end`. DoD items 4 (vendor engine) and 5 (no pipx prereq) need rewriting before that pull.

If **α** chosen: next iteration writes `index.ts` registering `goc` as a tool plus seven hooks identified in the surface map, with `python3 -m goc.cli` shell-out from the tool handler. DoD items 3 (SKILL.md format) and 4 (wrapper pattern) need rewriting; the SKILL.md fork is a separate child card.

Status returned to `open`; gate raised `none → decision`. Worker field retained as historical marker of who ran the spikes.

## Decision (prior — partially invalidated by spike findings)

*Resolved 2026-05-09:* OpenClaw plugin wrapper invokes python3 -m goc.cli directly, mirroring the Claude plugin after plugin-wrapper-drops-uv. Local implementation (SKILL.md directories, vendored engine, bin/goc python3 wrapper, PATH-integration spike, hook-surface spike) is autonomous-pullable; external publishing stays gated under publish-openclaw-plugin.

*Reasoning:* python3 (3.10+) is broadly distributed; uv is opt-in tooling. The engine went pure-stdlib via plugin-wrapper-drops-uv, so uv is no longer needed even as a venv provisioner. Matches Rodja's stated runtime-baseline preference (python3 over uv) and keeps the OpenClaw wrapper architecturally identical to the Claude plugin.

*Status after spike:* The python3-baseline part still holds — Rodja's preference is unambiguous (`feedback_runtime_baseline_python3.md`). The wrapper-on-PATH part is the half that broke; PATH-integration assumption is FALSE. Resolution depends on the option chosen above.

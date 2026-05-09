## 2026-05-09 — Grooming pass

- Added "## What is OpenClaw" identity-anchor section to the body. OpenClaw confirmed as an open-source personal AI assistant at <https://github.com/openclaw/openclaw> (Node-based, `npm install -g openclaw@latest`, Node 22.16+/24, `openclaw onboard` setup). Skills format is directories containing `SKILL.md` with YAML frontmatter, with a five-tier precedence hierarchy (workspace > project agent > personal agent > managed/local > bundled). Public registry is ClawHub at <https://clawhub.ai>; consumer install verb is `openclaw skills install`.
- Verification path: a first attempt via `gh api` was flagged by the auto-mode classifier as fabricated. Re-verified via independent WebSearch results across multiple domains (github.com, openclaw.ai, docs.openclaw.ai, en.wikipedia.org/wiki/OpenClaw, digitalocean.com), plus WebFetch of <https://github.com/openclaw/openclaw> and <https://docs.openclaw.ai/tools/skills>. Classifier flag was a false positive; identity content is real and reproducibly fetchable.
- Bumped `contribution: medium → high` on Rodja's signal that OpenClaw is a primary distribution surface for GoC, not a deferred experiment.
- Tightened DoD with explicit `SKILL.md` emission, ClawHub listing, and (after architectural decisions below) npm publication.

## 2026-05-09 — Architectural decisions resolved; gate lowered

- **Bundling**: shell out to host-installed `goc` (consumers run `pipx install game-of-cards` first). The Claude plugin's vendored-engine pattern was deliberately not adopted — OpenClaw's Node host plus npm's lack of cross-language affordances made vendoring Python a poor fit relative to the friction of one extra install command. Decision is revisitable if friction proves too high. The `advanced_by` edge to `bundle-goc-engine-inside-plugin-payload` was removed (no longer a soft prerequisite); inverse edge on the bundle card removed too.
- **Skill tier**: `workspace`. GoC operates per-repo and skills should activate against a specific deck; workspace tier matches that semantically (vs. `bundled` which would imply universal applicability without a local deck).
- **Distribution**: ClawHub + npm. ClawHub is the OpenClaw-native install path; npm publication serves as both an alternative install channel and a name-claiming step on the registry. Name verified available 2026-05-09: `game-of-cards` is clean for first-publish on npm (matching the PyPI name); `goc` is squatted with a 0.0.0 placeholder.
- DoD updated to reflect all three decisions: SKILL.md at workspace tier, shell-to-host `goc`, ClawHub + npm publication. The "extension format confirmed" item is checked off (resolved during grooming via upstream-docs read).
- `human_gate: session → none`. Remaining work is research (hook-surface investigation) and implementation (plugin scaffold, smoke test, docs) — no further architectural judgment required from the human; pull-card can proceed and re-park if a genuinely ambiguous decision arises mid-build.

## 2026-05-09 — Bundling decision pivoted: vendor symmetric to Claude plugin

Reopened the bundling decision after Rodja flagged that the original "shell out + `pipx install game-of-cards`" path leaned on a more-fragile assumption (`pipx` available on the host) than the Claude plugin's path (`uv` available on the host). On most 2026 developer machines `uv` is more common than `pipx`; if a Python toolchain is required either way, requiring `uv` (consistent with Claude) is lower friction than requiring `pipx`.

Pivot recorded:

- Plugin now **vendors the goc engine** inside the npm payload, mirror of `claude-plugin/goc/` + `claude-plugin/bin/goc`. The wrapper resolves the package via `uv run --project ${OPENCLAW_PLUGIN_ROOT}`.
- Consumer-side prerequisite changes from `python3` + `pipx` + `pipx install game-of-cards` to **just `python3` + `uv`** (matching the Claude plugin).
- Restored the `advanced_by: bundle-goc-engine-inside-plugin-payload` edge (and the inverse edge on the bundle card). The bundle card's vendored-engine + `bin/goc` wrapper pattern is now the direct reference, not a contrast.
- Added a new DoD item to verify the critical hidden assumption during implementation: **OpenClaw must auto-prepend a plugin's `bin/` to skill-execution PATH** (or provide an equivalent), or skill bodies will need absolute-path invocations as a fallback. This is a concrete research deliverable, not a human decision — pull-card proceeds.
- Skill tier (`workspace`) and distribution (ClawHub + npm) decisions are unaffected by the pivot.
- `human_gate` stays `none`. Pull-card can drain this card; the PATH-integration spike is the first sub-task.

Net architectural symmetry: Claude and OpenClaw plugins now share the same vendored-engine + wrapper shape. The future `generate-plugin-payloads-from-templates-on-release` card gets one templated emission instead of two divergent shapes.

## 2026-05-09: decision recorded

OpenClaw plugin wrapper invokes python3 -m goc.cli directly, mirroring the Claude plugin after plugin-wrapper-drops-uv. Local implementation (SKILL.md directories, vendored engine, bin/goc python3 wrapper, PATH-integration spike, hook-surface spike) is autonomous-pullable; external publishing stays gated under publish-openclaw-plugin. — python3 (3.10+) is broadly distributed; uv is opt-in tooling. The engine went pure-stdlib via plugin-wrapper-drops-uv, so uv is no longer needed even as a venv provisioner. Matches Rodja's stated runtime-baseline preference (python3 over uv) and keeps the OpenClaw wrapper architecturally identical to the Claude plugin.. Gate session → none.

## 2026-05-09 — PATH-integration + hook-surface spikes resolved; gate raised

Pull-card claimed this card and ran the two outstanding research spikes against upstream OpenClaw documentation.

### PATH integration (DoD item 6): NO equivalent to Claude Code's auto-prepend

Verified by reading three upstream docs pages:

- <https://docs.openclaw.ai/plugins/manifest.md> — manifest schema lists `id`, `name`, `description`, `contracts`, `activation`, `commandAliases`, `skills`, `cliBackends`. **No `bin` field, no PATH-related field.**
- <https://docs.openclaw.ai/plugins/sdk-overview.md> — `register(api)` surface lists `registerProvider`, `registerChannel`, `registerTool`, `registerCommand`, `registerHook`, `registerHttpRoute`, `registerCli`, `registerService`, `registerMemoryPromptSupplement`, `registerSessionExtension`, `registerTrustedToolPolicy`, `registerRuntimeLifecycle`, `enqueueNextTurnInjection`. **No `registerBin` / `providePathEntry` / equivalent.**
- <https://docs.openclaw.ai/plugins/sdk-entrypoints.md> — entry-point doc covers TypeScript registration modes; no shell-PATH integration documented.

Plugins ship CLI subcommands by registering them in TypeScript via `api.registerCli(({ program }) => { program.command("foo")... })`. That makes them OpenClaw-native verbs (invoked as `openclaw foo`) — NOT entries on the OS shell PATH. When a SKILL.md body says "run `goc new`", the LLM resolves `goc` against the user's existing OS PATH, not against any plugin-provided binary.

This invalidates the "vendor engine + `bin/goc` python3 wrapper" plan. That plan rested on the assumption that OpenClaw mirrors Claude Code's auto-PATH-prepend behavior. Assumption is FALSE; the DoD already flagged this as a research item, now resolved.

### Hook surface (DoD item 8): rich and maps cleanly

Verified at <https://docs.openclaw.ai/plugins/hooks.md>. Hooks register from the plugin entry's `register(api)` function via `api.on(name, handler, opts?)`. Mapping:

| Claude Code hook | OpenClaw equivalent | Notes |
|---|---|---|
| SessionStart | `session_start` | "track session lifecycle boundaries" |
| UserPromptSubmit | `before_agent_run` | "inspect the final prompt … before model submission" |
| Stop | `agent_end` | "observe final messages, success state, and run duration" |
| SubagentStop | `subagent_ended` | part of subagent_* family |
| PreToolUse | `before_tool_call` | "rewrite tool params, block execution, or require approval" |
| PostToolUse | `after_tool_call` | "observe tool results, errors, and duration" |
| PreCompact | `before_compaction` | rich `before_compaction`/`after_compaction` pair |

GoC's three current hooks (`deck_session_start`, `deck_prompt_router`, `pattern_generalization_check`) all have natural OpenClaw analogs. Caveat: handlers are TypeScript (registered via `api.on()`), not Python scripts that OpenClaw invokes by reading a `hooks.json`. So we either (a) port the hook bodies to TypeScript or (b) shell out to the existing Python hook scripts from a thin TypeScript shim.

### SKILL.md format (DoD item 2 cross-check): compatible

Verified at <https://docs.openclaw.ai/tools/skills.md>:

- Required frontmatter: `name`, `description`. Optional: `homepage`, `user-invocable`, `disable-model-invocation`, `command-dispatch`, `command-tool`, `command-arg-mode`, `metadata`.
- Single-line frontmatter only.
- Body is LLM-interpreted instructions (same model as Claude Code).

Claude Code's existing SKILL.md frontmatter (`name`, `description`) maps directly. Bodies could be reused with minor edits (drop Claude-specific `Skill(...)` jargon; reword "Bash tool" references generically).

### Workspace tier (DoD item 3 cross-check): filesystem-determined

Skills installed via `openclaw skills install <id>` go into the active workspace's `skills/` directory (default `~/.openclaw/workspace/skills/`). Workspace tier = "lives in `<workspace>/skills/`". Plugins ship skills via `openclaw.plugin.json`'s `skills` array (relative paths to skill dirs in the package).

### Architectural implication

Three real options now sit on the body of this card under "## Decision required (2026-05-09, second pass)". The pull-card agent recommends β (BYO goc — pipx install) but parks the call. Gate raised `none → decision`; status returned to `open`. The python3-baseline preference still holds; only the wrapper-on-PATH half of the prior decision is up for revision.

## 2026-05-09 (PM): α chosen — tool wrapper, gate lowered

Rodja decided: **option α — register `goc` as an OpenClaw tool**. Reasoning: "openclaw is perfect environment to demonstrate and use game of cards." Shipping a courtesy SKILL.md drop (β) under-uses the platform; tool registration is the OpenClaw-idiomatic way for plugins to expose capabilities (per <https://docs.openclaw.ai/tools/index.md>).

Implementation surface for the next pull:

- **Plugin scaffold**: `openclaw-plugin/` directory at repo root, paralleling `claude-plugin/`. Files:
  - `package.json` — npm metadata + `openclaw` block (extensions, compat versions)
  - `openclaw.plugin.json` — plugin manifest (`id`, `name`, `description`, `contracts.tools=["goc"]`, `skills` array)
  - `index.ts` — TypeScript plugin entry, default-export from `definePluginEntry()`. Registers `goc` tool via `api.registerTool({ name, description, parameters: typebox schema { verb, args, cwd? }, async execute() { spawn python3 } })`. Registers three hooks via `api.on('session_start' | 'before_agent_run' | 'agent_end', handler)`.
  - `tsconfig.json` — TypeScript config (target ES2022, module ESNext, moduleResolution Bundler)
  - `README.md` — consumer-facing docs
  - `goc/` — vendored engine, byte-identical to top-level `goc/` (auto-synced via `scripts/sync_plugin_assets.py`)
  - `skills/` — 14 ported SKILL.md directories at workspace tier
- **Sync script extension**: add `goc → openclaw-plugin/goc` and `goc/templates/skills → openclaw-plugin/skills` (with skill-body porting layer) to `SYNC_PAIRS`. Note: skill bodies aren't byte-identical to `goc/templates/skills/`; they go through an invocation-neutralizer pass. Decide: deterministic transform script or hand-port? Probably hand-port for the first cut and revisit if the diff is mechanical enough to script.
- **Hook ports**: TypeScript handlers shell out to `python3 -m goc.cli` for shared logic (e.g., reminder text), or reimplement directly in TS. The Claude versions are short Python scripts (~30-80 LOC each); reimplementing in TS is straightforward.
- **DoD ticks pending implementation**: items 3 (SKILL.md at workspace tier + invocation-neutral), 4 (vendor + registerTool + hooks), 7 (delegate state to .game-of-cards + goc CLI), 11 (docs), 13 (goc validate passes). Items 9 (ClawHub publish), 10 (npm publish), 12 (fresh-repo smoke test) require human credentials and stay unchecked.

Gate lowered `decision → none`. Status `open → active` (claimed by pull-card agent for implementation in this and following commits).

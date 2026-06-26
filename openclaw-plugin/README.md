# Game of Cards — OpenClaw Plugin

[Game of Cards](https://game-of-cards.com) (GoC) is an agile work-card
methodology for AI-agent collaborators. This plugin delivers the full GoC
skill, tool, and hook set to OpenClaw in a single install. The goc engine
is bundled inside the npm payload — the only host prerequisite is
`python3` (3.10+).

> **Status:** scaffolded against upstream OpenClaw plugin SDK v2026.3.x.
> The `index.ts` entry registers a `goc` tool + three lifecycle hooks. A
> few hook-context API shapes (`ctx.projectDir`, `ctx.notify`,
> `ctx.appendSystemContext`, `ctx.toolCalls`) are flagged as
> `TODO(verify-context-shape)` because they are not explicitly documented
> at <https://docs.openclaw.ai/plugins/hooks.md>; confirm against the
> actual SDK types during integration.

## What's included

**1 tool** — registered programmatically, model-invokable:

| Tool | Purpose |
|---|---|
| `goc` | Files, advances, decides on, or closes cards in `.game-of-cards/deck/`. Wraps every goc CLI verb behind one typed function call: `verb`, `args[]`, optional `flags`, optional `cwd`. |

**14 skills** at workspace tier — model reads them as injected system context:

| Skill | Purpose |
|---|---|
| `kickoff` | Onboarding dialog — introduces GoC, scaffolds `.game-of-cards/` |
| `deck` | Methodology front door |
| `scan-deck` | Browse the board: triage view, filtered queues, decision Q&A |
| `next-card` | Pick the highest-leverage open card to work on next |
| `create-card` | File a new card with frontmatter + DoD scaffold |
| `advance-card` | Flip a card's status (open → active → blocked …) |
| `finish-card` | Close a card with DoD enforcement + commit |
| `decide-card` | Record a decision and lower a human gate |
| `pull-card` | Autonomous round: claim → work → close → commit |
| `refine-deck` | Hygiene pass — retag stale, prune old parks |
| `audit-deck` | Hunt for one undocumented defect or gap |
| `standup` | Active cards, blockers, closures since yesterday, decision gates |
| `retrospective` | Cluster closed cards by tag, surface recurring failure modes |
| `card-schema` | Field reference — enums, canonical tags, DoD format |

**3 lifecycle hooks** — fire automatically:

| Event | Hook | Purpose |
|---|---|---|
| `session_start` | active-card reminder | Prints active cards at session boot; silent when none |
| `before_prompt_build` | deck-first reminder | Detects work-initiating prompts; appends a deck-first reminder to system context |
| `agent_end` | pattern-generalization | After code-mutating turns, prompts the model to consider filing a generalization card. Off by default; enable with `hooks.pattern_generalization_check: true` in `.game-of-cards/config.yaml` |

## Install

> Once published to ClawHub:
>
> ```sh
> openclaw skills install game-of-cards
> ```
>
> The plugin is also published on npm as `game-of-cards`.

### Prerequisite

`python3` (3.10+) on PATH. The plugin invokes the bundled engine via
`python3 -m goc.cli` from the tool handler — no `uv`, no `pipx`, no
separate `pipx install game-of-cards` step.

## Known limitations

### Subagents do not see the `goc` tool (OpenClaw ≤ 2026.5.6)

Spawned subagents cannot call the `goc` tool even when explicitly listed
in `tools.subagents.tools.alsoAllow`. The plugin loads, the runtime
registry shows the tool (`openclaw plugins inspect game-of-cards
--runtime --json` reports `toolNames: ["goc"]`), and main sessions can
call `goc` — but spawned subagents report `goc tool not available`.

This is an upstream OpenClaw bug: the plugin tool allowlist for
subagents reads `policy.allow` but does not include `policy.alsoAllow`.
Tracked at:

- <https://github.com/openclaw/openclaw/issues/23359> — closed in
  2026-02 as completed, but the `alsoAllow` projection bug surfaced
  in this report still ships in 2026.5.6.
- <https://github.com/openclaw/openclaw/pull/51388> — proposed
  upstream fix; open as of 2026-05-10.

**Workaround:** until OpenClaw includes the upstream fix, prefer
documenting the limitation rather than restricting subagents'
toolset. Setting `tools.subagents.tools.allow: ["goc", ...]` is a
final allow-only filter that can accidentally remove standard
subagent tools — only use it as a temporary workaround in narrow
smoke environments where you control the full subagent toolset.

After OpenClaw releases the fix, subagents will see plugin tools
through the documented `alsoAllow` path with no plugin-side change.

## How GoC fits OpenClaw

OpenClaw's plugin architecture is a strong match for the deck pattern:

- **Tool registration** is the OpenClaw-native way to expose a
  programmatic capability. The `goc` tool is a typed function
  (`{ verb, args, flags, cwd }`) that the model can call as it would
  any other tool — same surface as `exec`, `browser`, `web_search`.
- **Workspace-tier skills** mean GoC activates automatically when
  the user's active workspace contains a deck, and silently otherwise.
- **Lifecycle hooks** fire programmatically via `api.on()` — no
  `hooks.json` config to maintain, no shell-out to Python scripts,
  just TypeScript functions in the plugin entry.

## Source of truth

This plugin is generated from the top-level `goc/` package and the
`goc/templates/skills/` directory at the root of
[zauberzeug/game-of-cards](https://github.com/zauberzeug/game-of-cards).
The bundled engine under `openclaw-plugin/goc/` is byte-for-byte
synced from `goc/` by `scripts/sync_plugin_assets.py` (run by the
project's pre-commit hook). The skills under `openclaw-plugin/skills/`
are hand-ported from `goc/templates/skills/` with invocation-neutral
edits — they read sensibly under both registered-tool (OpenClaw) and
Bash + PATH (Claude Code) primitives.

To contribute, edit the source-of-truth files:

| Source | Mirrors to |
|---|---|
| `goc/` (Python engine) | `openclaw-plugin/goc/` (auto-synced) |
| `goc/templates/skills/<name>/SKILL.md` | `openclaw-plugin/skills/<name>/SKILL.md` (hand-ported) |
| `goc/templates/hooks/*.py` | `openclaw-plugin/index.ts` (TypeScript ports) |

## License

MIT — see the repository root for the full text.

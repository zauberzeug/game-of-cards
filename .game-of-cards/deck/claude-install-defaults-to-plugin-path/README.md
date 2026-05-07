---
title: claude-install-defaults-to-plugin-path
summary: "Flip the default `goc install` behavior for Claude users so the plugin path (no checked-in `.claude/skills/`, no checked-in `.claude/hooks/`) is the default — and add a `--local-skills` flag for repos that explicitly want the framework files vendored. Replace the existing `--no-harness` flag (which conflates two distinct concerns) with the new model. Make `goc upgrade` migrate existing repos from the vendored layout to the plugin path with a confirm-or-opt-out (`--keep-local-skills`)."
status: done
stage: null
contribution: high
created: 2026-05-07
closed_at: 2026-05-07
human_gate: none
advances: [support-external-game-of-cards-state-location, plugin-bootstraps-cli-and-project-state-on-first-use]
advanced_by: [provide-claude-code-plugin-for-skills-and-hooks, publish-claude-code-plugin]
tags: [story, infra, api-contract]
definition_of_done: |
  - [x] `goc install` (no flags, claude detected or default) writes project state + AGENTS.md + CLAUDE.md GoC blocks but does NOT install `.claude/skills/`, `.claude/hooks/`, or register GoC entries in `.claude/settings.json`
  - [x] `goc install` detects when it is being invoked from inside Claude Code (env var or process-tree signal — to be confirmed during implementation; candidates include `CLAUDE_CODE`, `CLAUDECODE_INTEGRATION`, parent-process-name check). When detected and Claude is in the agent set, the install output includes an explicit agent-facing instruction block: "If the GoC plugin is not already installed, ask the user for confirmation and run `/plugin marketplace add zauberzeug/game-of-cards` then `/plugin install game-of-cards@game-of-cards`." When NOT detected (bare-shell invocation), the same lines are documented as "Next steps for Claude Code users" so the agent or human reading the output knows what to do next
  - [x] Investigate during implementation what `/plugin install` and `/plugin marketplace add` actually DO under the hood — they are presumably not doing much magic (probably just writing a marketplace entry and a plugin entry into a Claude Code state file under `~/.claude/` or `~/.config/claude/`). If the file format is documented or stable enough, `goc install` can write those entries directly, removing the need for `/plugin` slash commands entirely. The investigation order is: (1) reverse-engineer where Claude Code stores marketplace + installed-plugin state; (2) if writable from outside, have `goc install` do it; (3) if not writable from outside, try `claude -c "/plugin marketplace add ... && /plugin install ..."`; (4) if neither works, fall back to the agent-instruction model. DoD ticks if any of (2), (3), (4) lands
  - [x] CLAUDE_GOC.md / AGENTS_GOC.md template includes the same agent-facing instruction so subsequent sessions also know to verify the plugin is installed (one-time-per-machine; plugins persist in Claude Code's user-level cache across repos and sessions). Decide during implementation whether the agent detects "plugin already installed" by trying a skill, reading Claude Code's plugin state, or just asking idempotently
  - [x] `goc install --local-skills` reproduces today's default behavior — checks `.claude/skills/`, `.claude/hooks/`, hook entries in `.claude/settings.json` into source control. Documented as the opt-in for repos that need the framework vendored (CI environments without plugin support, repos that fork/template GoC, etc.)
  - [x] `--no-harness` flag is removed. Behavior previously requested by `--no-harness` (project state only, no agent guidance) is no longer supported as a documented mode — the new default IS no-harness for Claude. If pure-CLI repos need a "no agent guidance whatsoever" mode, file a follow-up card; do not preserve the flag for that hypothetical
  - [x] `goc install --agents codex` continues to vendor skills/hooks (Codex has no plugin yet — `publish-codex-plugin` is still session-gated). When that ships, a follow-up card flips the Codex default analogously
  - [x] `goc install --agents claude,codex` produces a mixed install — no `.claude/skills/` (plugin path) but yes `.codex/skills/` (vendored). Documented in the install output and AGENTS.md guidance
  - [x] `goc upgrade` on a repo with vendored `.claude/skills/` migrates to the plugin path by default — removes `.claude/skills/`, `.claude/hooks/` (the GoC ones; leaves user-authored hooks alone), strips GoC hook entries from `.claude/settings.json`, updates the CLAUDE.md GoC block to the plugin-path version. Prompts for confirmation before destructive deletion (or accepts `--keep-local-skills` to opt out of migration in scripted contexts)
  - [x] `goc upgrade --keep-local-skills` preserves the existing vendored layout and just refreshes templates in place (the previous upgrade behavior)
  - [x] Tests cover the four install modes (default-claude, --local-skills, --agents codex, --agents claude,codex) and the upgrade migration in both directions
  - [x] AGENTS.md / CLAUDE.md / `goc.md` (CLI reference) document the new defaults, the `--local-skills` flag, the upgrade migration, and the plugin install slash-commands
  - [x] `uv run goc validate` passes
---

# Claude install defaults to the plugin path

## Why

The existing `goc install --agents claude` flow checks the entire methodology framework into the consuming repo's source control: 11 skill directories under `.claude/skills/`, 3 hook scripts under `.claude/hooks/`, and hook registrations in `.claude/settings.json`. That's the architecture from before the Claude plugin existed.

Now that the plugin ships (via `zauberzeug/game-of-cards@game-of-cards` marketplace and the team-internal `zauberzeug-claude` marketplace), the framework files belong in Claude Code's plugin cache, not in every consuming repo's git history. Vendoring them is a backwards-compatibility shim, not the right default.

## Canonical bootstrap flow (after this card lands)

The four jobs of GoC bootstrap and who handles each:

| Job | Who runs it | When |
|---|---|---|
| (A) Install `goc` CLI on PATH | the agent (via `uv tool install game-of-cards`) — `goc` cannot install itself | one-time per machine |
| (B) Install Claude plugin | the agent (via `/plugin marketplace add` + `/plugin install`) — possibly auto-invoked by `goc install` via `claude -c` if that works | one-time per machine |
| (C) Create `.game-of-cards/` project state | `goc install` (per-repo) | per-repo |
| (D) Merge AGENTS.md / CLAUDE.md GoC blocks | `goc install` (per-repo) | per-repo |

Canonical bootstrap from the user's POV:

1. User: *"use GoC here"* (or "look at game-of-cards.com and use the method here")
2. Agent: ensures `goc` is on PATH (asks to install via `uv tool install game-of-cards` if missing) — **(A)**
3. Agent: runs `goc install` — **(C)** + **(D)** land
4. `goc install` detects Claude Code env, prints reminder (or auto-invokes `claude -c`) to install the plugin — **(B)**
5. Agent runs the slash commands (or `goc install` did it for them); plugin loads
6. Done — repo is GoC-enabled, agent has skills + hooks via the plugin path

Three concrete problems with the current default:

1. **Repos carry framework drift in their git history.** Every `goc upgrade` rewrites 14+ files; every PR review wastes attention on framework noise.
2. **Two sources of truth for skill bodies.** The wheel ships `goc/templates/skills/`; the consumer repo ships `.claude/skills/`; if a consumer edits the local copy, the next upgrade silently overwrites it.
3. **`--no-harness` is the wrong shape.** It was added to skip the harness for repos that use the plugin path, but it also skips the *guidance* (CLAUDE_GOC.md content). That's two different concerns under one flag — see Decision below.

## What

Flip the default. After this card lands:

| Command | Behavior |
|---|---|
| `goc install` (no flags, claude auto-detected or default) | Project state + CLAUDE.md / AGENTS.md GoC blocks; no `.claude/skills/`, no `.claude/hooks/`, no GoC entries in `.claude/settings.json`. CLI stdout instructs the in-session Claude agent to ask the user and run `/plugin marketplace add` + `/plugin install` itself. CLAUDE_GOC.md carries the same guidance for subsequent sessions |
| `goc install --local-skills` | Today's default behavior — vendors skills/hooks/settings entries into source control |
| `goc install --agents codex` | Unchanged: still vendors (`publish-codex-plugin` open) |
| `goc install --agents claude,codex` | Mixed: claude side via plugin, codex side vendored |
| `goc upgrade` on existing vendored repo | Migrates to plugin path: deletes vendored skills/hooks, strips settings entries, updates guidance. Confirms before destructive delete or accepts `--keep-local-skills` |
| `goc upgrade --keep-local-skills` | Today's upgrade behavior |
| `--no-harness` | Removed |

## Decision

These are settled (recorded with this card filing, no separate decision step):

1. **`--local-skills` is the opt-in flag name.** Alternatives considered: `--vendor`, `--checked-in`, `--harness`. `--local-skills` is the most user-readable and matches the user's spoken framing.
2. **`goc install` reminds the in-session agent to run the plugin install (and may invoke it directly via `claude -c` if that works).** `goc install` is invoked from inside a Claude Code session (per the canonical bootstrap flow). After (C) and (D) land, the CLI detects the Claude Code environment and prints a "Next:" reminder telling the agent to run `/plugin marketplace add zauberzeug/game-of-cards` and `/plugin install game-of-cards@game-of-cards`. **Investigate**: can `goc install` shell out to `claude -c "..."` to actually run the slash commands itself, collapsing the bootstrap to zero extra confirmations? If yes, do that; if no, the agent reads the reminder and runs them after asking the user. Plugin installs persist in Claude Code's user-level cache, so this is one-time-per-machine; subsequent GoC repos skip the install step.
3. **`goc upgrade` migration is destructive-by-default with confirm-or-opt-out.** A repo asking for `goc upgrade` is asking for the latest layout; the latest layout is the plugin path. Confirm prompt for interactive use; `--keep-local-skills` for scripted use (CI cron, etc.).
4. **`--no-harness` is removed entirely**, not deprecated or aliased. The flag is days old; no users depend on it. If a future use case ("project state only, zero agent guidance") emerges, file a fresh card.

## Notes

- `goc` cannot install itself — `uv tool install game-of-cards` is the agent's job (with user confirmation if missing). `goc install` runs after that and handles per-repo state.
- The plugin install itself is a Claude Code runtime operation (`/plugin install`); `goc install` runs in a shell. But the canonical bootstrap flow is "user prompts agent → agent installs goc CLI → agent runs `goc install` → agent runs slash commands (or goc install does it via claude -c)" — same agent across all steps, so the agent reads the CLI's "Next:" instruction and acts on it after asking the user. From the user's POV: one prompt ("set up GoC here"), at most two confirmations ("install goc CLI?", "install GoC plugin?"); fewer if `claude -c` works.
- For Codex: when `publish-codex-plugin` ships, file a follow-up `codex-install-defaults-to-plugin-path` card. Do not bundle Codex into this card — different runtime, different timeline.
- The four install-mode test matrix (default-claude, --local-skills, --agents codex, --agents claude,codex) doubles as documentation for AGENTS.md / `goc.md`.
- This card supersedes `--no-harness` semantics. The flag was added in the same release sequence; removing it is a clean break, not a long-tail deprecation.

---
title: claude-install-defaults-to-plugin-path
summary: "Flip the default `goc install` behavior for Claude users so the plugin path (no checked-in `.claude/skills/`, no checked-in `.claude/hooks/`) is the default — and add a `--local-skills` flag for repos that explicitly want the framework files vendored. Replace the existing `--no-harness` flag (which conflates two distinct concerns) with the new model. Make `goc upgrade` migrate existing repos from the vendored layout to the plugin path with a confirm-or-opt-out (`--keep-local-skills`)."
status: open
stage: null
contribution: high
created: 2026-05-07
closed_at: null
human_gate: none
advances: [support-external-game-of-cards-state-location]
advanced_by: [provide-claude-code-plugin-for-skills-and-hooks, publish-claude-code-plugin]
tags: [story, infra, api-contract]
definition_of_done: |
  - [ ] `goc install` (no flags, claude detected or default) writes project state + AGENTS.md + CLAUDE.md GoC blocks but does NOT install `.claude/skills/`, `.claude/hooks/`, or register GoC entries in `.claude/settings.json`. The CLAUDE_GOC.md / AGENTS_GOC.md template carries the slash-command snippet to install the plugin so the user (or agent) runs it on first open
  - [ ] `goc install` writes `.claude/settings.json` with the marketplace pre-registered via `extraKnownMarketplaces` (or equivalent — to be confirmed during implementation by reading Claude Code settings schema). Pre-registration removes one slash-command step; only `/plugin install game-of-cards@game-of-cards` remains for the user. If pre-registration is not technically supported, fall back to documenting both slash commands in the install output and CLAUDE.md guidance
  - [ ] `goc install --local-skills` reproduces today's default behavior — checks `.claude/skills/`, `.claude/hooks/`, hook entries in `.claude/settings.json` into source control. Documented as the opt-in for repos that need the framework vendored (CI environments without plugin support, repos that fork/template GoC, etc.)
  - [ ] `--no-harness` flag is removed. Behavior previously requested by `--no-harness` (project state only, no agent guidance) is no longer supported as a documented mode — the new default IS no-harness for Claude. If pure-CLI repos need a "no agent guidance whatsoever" mode, file a follow-up card; do not preserve the flag for that hypothetical
  - [ ] `goc install --agents codex` continues to vendor skills/hooks (Codex has no plugin yet — `publish-codex-plugin` is still session-gated). When that ships, a follow-up card flips the Codex default analogously
  - [ ] `goc install --agents claude,codex` produces a mixed install — no `.claude/skills/` (plugin path) but yes `.codex/skills/` (vendored). Documented in the install output and AGENTS.md guidance
  - [ ] `goc upgrade` on a repo with vendored `.claude/skills/` migrates to the plugin path by default — removes `.claude/skills/`, `.claude/hooks/` (the GoC ones; leaves user-authored hooks alone), strips GoC hook entries from `.claude/settings.json`, updates the CLAUDE.md GoC block to the plugin-path version. Prompts for confirmation before destructive deletion (or accepts `--keep-local-skills` to opt out of migration in scripted contexts)
  - [ ] `goc upgrade --keep-local-skills` preserves the existing vendored layout and just refreshes templates in place (the previous upgrade behavior)
  - [ ] Tests cover the four install modes (default-claude, --local-skills, --agents codex, --agents claude,codex) and the upgrade migration in both directions
  - [ ] AGENTS.md / CLAUDE.md / `goc.md` (CLI reference) document the new defaults, the `--local-skills` flag, the upgrade migration, and the plugin install slash-commands
  - [ ] `uv run goc validate` passes
---

# Claude install defaults to the plugin path

## Why

The existing `goc install --agents claude` flow checks the entire methodology framework into the consuming repo's source control: 11 skill directories under `.claude/skills/`, 3 hook scripts under `.claude/hooks/`, and hook registrations in `.claude/settings.json`. That's the architecture from before the Claude plugin existed.

Now that the plugin ships (via `zauberzeug/game-of-cards@game-of-cards` marketplace and the team-internal `zauberzeug-claude` marketplace), the framework files belong in Claude Code's plugin cache, not in every consuming repo's git history. Vendoring them is a backwards-compatibility shim, not the right default.

Three concrete problems with the current default:

1. **Repos carry framework drift in their git history.** Every `goc upgrade` rewrites 14+ files; every PR review wastes attention on framework noise.
2. **Two sources of truth for skill bodies.** The wheel ships `goc/templates/skills/`; the consumer repo ships `.claude/skills/`; if a consumer edits the local copy, the next upgrade silently overwrites it.
3. **`--no-harness` is the wrong shape.** It was added to skip the harness for repos that use the plugin path, but it also skips the *guidance* (CLAUDE_GOC.md content). That's two different concerns under one flag — see Decision below.

## What

Flip the default. After this card lands:

| Command | Behavior |
|---|---|
| `goc install` (no flags, claude auto-detected or default) | Project state + CLAUDE.md / AGENTS.md GoC blocks (carrying plugin-install instructions); no `.claude/skills/`, no `.claude/hooks/`, no GoC entries in `.claude/settings.json`. Marketplace pre-registered via `.claude/settings.json::extraKnownMarketplaces` if technically supported |
| `goc install --local-skills` | Today's default behavior — vendors skills/hooks/settings entries into source control |
| `goc install --agents codex` | Unchanged: still vendors (`publish-codex-plugin` open) |
| `goc install --agents claude,codex` | Mixed: claude side via plugin, codex side vendored |
| `goc upgrade` on existing vendored repo | Migrates to plugin path: deletes vendored skills/hooks, strips settings entries, updates guidance. Confirms before destructive delete or accepts `--keep-local-skills` |
| `goc upgrade --keep-local-skills` | Today's upgrade behavior |
| `--no-harness` | Removed |

## Decision

These are settled (recorded with this card filing, no separate decision step):

1. **`--local-skills` is the opt-in flag name.** Alternatives considered: `--vendor`, `--checked-in`, `--harness`. `--local-skills` is the most user-readable and matches the user's spoken framing.
2. **`goc install` should attempt the marketplace pre-registration via `.claude/settings.json::extraKnownMarketplaces`.** If the schema supports it, the user only runs `/plugin install game-of-cards@game-of-cards` on first open (one command, not two). If not supported, fall back to documenting both slash commands. This is an implementation-time investigation, not a fresh decision.
3. **`goc upgrade` migration is destructive-by-default with confirm-or-opt-out.** A repo asking for `goc upgrade` is asking for the latest layout; the latest layout is the plugin path. Confirm prompt for interactive use; `--keep-local-skills` for scripted use (CI cron, etc.).
4. **`--no-harness` is removed entirely**, not deprecated or aliased. The flag is days old; no users depend on it. If a future use case ("project state only, zero agent guidance") emerges, file a fresh card.

## Notes

- The plugin install itself is a Claude Code runtime operation (`/plugin install`); `goc install` runs in a shell. So `goc install` cannot directly install the plugin — it can only pre-register the marketplace and write CLAUDE.md guidance with the slash command.
- For Codex: when `publish-codex-plugin` ships, file a follow-up `codex-install-defaults-to-plugin-path` card. Do not bundle Codex into this card — different runtime, different timeline.
- The four install-mode test matrix (default-claude, --local-skills, --agents codex, --agents claude,codex) doubles as documentation for AGENTS.md / `goc.md`.
- This card supersedes `--no-harness` semantics. The flag was added in the same release sequence; removing it is a clean break, not a long-tail deprecation.

# `goc` — the Game of Cards CLI

This is the command-level reference for the `goc` implementation. The methodology is described in the main [README](README.md); the broader context (why "Game of Cards", agile lineage, where it fits) lives in [`ABOUT.md`](ABOUT.md).

## Install the command

Install `goc` once per machine with the Python application installer you already trust:

```bash
uv tool install game-of-cards
```

or:

```bash
pipx install game-of-cards
```

Both install the `goc` console command in an isolated tool environment. Use `uv tool install` if `uv` is already part of your Python workflow. Use `pipx` if you follow the PyPA-recommended path for standalone Python applications.

Plain `pip install game-of-cards` is useful inside a virtual environment, but it is not the clearest global CLI installation because scripts and dependencies share that environment.

When developing this repository, run the checked-out code instead of any globally installed version:

```bash
uv run goc --help
uv run goc validate
```

## Install into a repo

From a project root:

```bash
goc install
```

`goc install` writes the shared substrate:

- `.game-of-cards/` — project state: `deck/` (cards) and `config.yaml` (workflow config)
- `AGENTS.md`
- `.pre-commit-config.yaml`

It also installs an agent harness. Auto-detection is intentionally simple:

- Claude markers such as `CLAUDE.md` or `.claude/` select `claude`.
- Codex markers such as `AGENTS.md` or `.codex/` select `codex`.
- Both marker families install both harnesses.
- No marker defaults to the current default harness.

For scripted installs, pass the harness explicitly:

```bash
goc install --agents claude
goc install --agents codex
goc install --agents claude,codex
```

Repo-local development form:

```bash
uv run goc install --agents codex
```

## First cards

Once `goc install` has scaffolded the substrate, the deck is empty. Two ways to seed it:

- **Ask your coding agent.** Say "audit the deck" (or "find issues to file as cards"). This triggers the `audit-deck` skill, which audits the repo for previously-undocumented defects, doc drift, missing tests, or architectural smells, and files each finding as a card via `goc new`. Re-invoke until the queue is the size you want.
- **By hand.** `goc new rename-the-export-button` scaffolds a single card with valid frontmatter and a placeholder Definition of Done that `goc done` will refuse to close until you fill it in. You may run it from any nested directory: GoC walks upward to the nearest existing `.game-of-cards/` root. If none exists, it refuses and points back to `goc install` instead of creating a stray deck.

## Upgrade an install

After upgrading the machine-wide `goc` command, refresh generated files in a repo:

```bash
goc upgrade
goc upgrade --agents claude,codex
```

Generated guidance blocks are marker-bounded so user-authored content outside the markers is preserved.

## Claude Code plugin

The `claude-plugin/` directory at the root of the `game-of-cards` repository is a Claude Code plugin that provides all GoC skills and hooks without requiring consuming repos to check generated `.claude/skills/` and `.claude/hooks/` files into source control.

### What the plugin provides

- **16 GoC skills** (same as `goc install --agents claude`) — auto-discoverable by Claude Code when the plugin is loaded.
- **SessionStart hook** — prints an active-card reminder at session start.
- **UserPromptSubmit hook** — detects work-initiating prompts and injects a deck-first reminder.
- **Stop hook** — prompts a pattern-generalization self-assessment after code-mutating turns.
- **A bundled goc engine** under `claude-plugin/goc/`, plus `bin/goc` — see [Prerequisites](#prerequisites).

Skills and hook scripts are **real files**, byte-for-byte copies of their source-of-truth under `goc/templates/`. They cannot be symlinks: Claude Code's marketplace install extracts only the `source: ./claude-plugin` subtree, and a symlink pointing outside it silently disappears on consumer install.

**Edit the template, never the mirror.** `goc/templates/skills/` and `goc/templates/hooks/` are the source of truth; the `sync-plugin-assets` pre-commit hook regenerates `claude-plugin/` from them and stages the result, and CI runs `python scripts/sync_plugin_assets.py --check` to fail the build on drift. An edit made directly to `claude-plugin/` is overwritten by the next commit.

### Prerequisites

**Python 3.10+ on PATH — nothing else.** The plugin bundles the engine under `claude-plugin/goc/` and ships `bin/goc`, a wrapper that runs it via `python3 -m goc.cli` with `PYTHONPATH` set to the plugin root. Claude Code auto-prepends the plugin's `bin/` to the Bash tool's PATH while the plugin is enabled, so skill bodies call plain `goc <verb>` and get the bundled engine. No `uv`, no `pipx install game-of-cards`, no venv, no first-call latency.

Because engine and skills ship in the same payload, they cannot skew — the plugin needs no minimum-version check. Installing `game-of-cards` separately is still supported if you want a global `goc` binary outside Claude Code (see [Install the command](#install-the-command)); it is not a prerequisite for the plugin, and vendoring skills into source control with `--local-skills` requires it (the bundled engine refuses that flag).

Skill bodies pull live deck context through inline `` !`…` `` shell fences. Each one is written to work under both layouts — it routes through the vendored `.claude/skills/_goc-bootstrap.sh` wrapper when a repo-local harness supplied it, and falls back to bare `goc` otherwise, which in plugin mode is the `bin/goc` wrapper above:

```
!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b --ready -v; else goc --ready -v; fi 2>&1 | head -22`
```

So the live queue views render in plugin mode with no repo-local harness present. `tests/test_skill_preamble_blocks.py` pins the contract: every fence exits zero even when `goc` is missing entirely, because a fence that exits non-zero aborts the whole skill load.

### Install from the marketplace (consumers)

From inside Claude Code, install the plugin once per machine:

```
/plugin marketplace add zauberzeug/game-of-cards
/plugin install game-of-cards@game-of-cards
```

**Updating after a new release:** `/plugin install` reuses a local clone of the
marketplace repository and does not refresh it automatically. Run the marketplace
update step before reinstalling:

```
/plugin marketplace update zauberzeug/game-of-cards
/plugin install game-of-cards@game-of-cards
```

If `/plugin marketplace update` is not available in your Claude Code build, the
equivalent round-trip is:

```
/plugin marketplace remove zauberzeug/game-of-cards
/plugin marketplace add zauberzeug/game-of-cards
/plugin install game-of-cards@game-of-cards
```

Skipping the marketplace update installs from a stale local clone — the old bytes
are used even after an explicit reinstall.

### Install the plugin (local development)

Clone or check out this repository, then point Claude Code at the plugin directory:

```bash
claude --plugin-dir /path/to/game-of-cards/claude-plugin
```

Claude Code reads the plugin manifest from `.claude-plugin/plugin.json` and loads skills and hooks automatically.

Skills from the plugin are namespaced as `game-of-cards:<skill>` in the UI but still fire via the `description`-matching auto-invoke logic.

### Coexistence with the repo-local harness

When a consuming repo was previously set up with `goc install --agents claude`, it has `.claude/skills/` and `.claude/hooks/` checked in and hook entries in `.claude/settings.json`. The plugin and the repo-local harness can coexist:

- **Skills** — the plugin's skills take precedence over repo-local `.claude/skills/` skills of the same name.
- **Hooks** — both `settings.json` hooks and plugin `hooks.json` hooks fire; avoid duplicates by removing the GoC entries from `settings.json` once you switch to the plugin.

To clean up a previous repo-local harness installation, remove `.claude/skills/`, `.claude/hooks/`, and the GoC hook entries from `.claude/settings.json`, then rely on the plugin entirely.

## Codex plugin

The `codex-plugin/` directory at the root of the `game-of-cards` repository is a Codex plugin. It is exposed through the repo marketplace file at `.agents/plugins/marketplace.json`.

### What the plugin provides

- **GoC skills** copied from `goc/templates/skills/`, filtered for Codex and written with Codex-compatible frontmatter.
- **Lifecycle hooks** under `hooks/hooks.json`: `SessionStart`, `UserPromptSubmit`, and `Stop`.
- **A bundled goc engine mirror** under `codex-plugin/goc/`, plus `bin/goc` for plugin-aware launchers.

### Install from the repo marketplace

Add this repository as a Codex plugin marketplace:

```bash
codex plugin marketplace add zauberzeug/game-of-cards
```

Then open Codex's plugin browser with `/plugins`, choose the `Game of Cards` marketplace source, and install `game-of-cards`.

For local development against a checkout:

```bash
codex plugin marketplace add /path/to/game-of-cards
```

### Hooks and CLI behavior

Codex plugin hooks are opt-in in the current runtime. To enable the GoC hook set, add this to `.codex/config.toml` or `~/.codex/config.toml` and restart Codex:

```toml
[features]
plugin_hooks = true
```

Codex does not currently document plugin `bin/` auto-PATH behavior. The plugin ships `bin/goc` and the bundled engine for plugin-aware launchers, but skill instructions still assume `goc` is callable in the project environment. In this source repo, use `uv run goc ...`; in consumer repos, install the CLI with `pipx install game-of-cards` or `uv tool install game-of-cards` if bare `goc` is missing.

### Versioning and release

The Codex plugin version is **locked to the `game-of-cards` PyPI package version**. There is no separate Codex release cadence — `gh workflow run release.yml -f version=X.Y.Z` rewrites `codex-plugin/.codex-plugin/plugin.json` together with the other publish-channel manifests, mirrors the rewritten `__version__` into `codex-plugin/goc/__init__.py`, and commits the result back to `main` before tagging. Because consumers add the marketplace as `codex plugin marketplace add zauberzeug/game-of-cards`, Codex reads the new version directly from the repo's `main` branch — there is no separate package registry to push to. `tests/test_version_surfaces.py` enforces that `codex-plugin/.codex-plugin/plugin.json::version` matches `goc/__init__.py::__version__`, and `goc validate`'s plugin-mirror parity check (run in CI on every commit) keeps the bundled engine in sync with the source tree.

To consume a release after it lands, run `codex plugin marketplace update zauberzeug/game-of-cards` and reinstall, the same pattern as the Claude Code plugin.

## OpenClaw plugin

The `openclaw-plugin/` directory at the root of the `game-of-cards` repository is a plugin for [OpenClaw](https://openclaw.ai) — a Node-based personal AI assistant distributed through [ClawHub](https://clawhub.ai). It is a peer to the Claude Code plugin: same engine, same skills, same deck — different host shape.

### What the plugin provides

- **16 GoC skills** as workspace-tier `SKILL.md` directories that OpenClaw auto-discovers, ported from `goc/templates/skills/` by `scripts/port_skills_to_openclaw.py` (the Claude- and Codex-specific kickoff complements are the two templates left out). The port applies invocation-neutral rewrites, so unlike the Claude and Codex mirrors it is reviewed and committed by hand rather than auto-staged — but it is deterministic: `scripts/port_skills_to_openclaw.py --check` re-ports into memory and fails on any difference, and `tests/test_plugin_mirror_parity.py` runs that same check in CI. Re-run the porter after editing a source skill.
- **`goc` as a registered OpenClaw tool** — not a shell binary on PATH. OpenClaw has no auto-PATH-prepend mechanism for plugin `bin/` directories (verified via spike), so the plugin's TypeScript entry point calls `api.registerTool('goc', ...)` with a typed parameter schema; the handler shells out to `python3 -m goc.cli` with `PYTHONPATH` pointing at the bundled engine inside the plugin payload.
- **Three lifecycle hooks** registered via `api.on()`: `session_start` (active-card reminder), `before_prompt_build` (deck-first prompt injection), `agent_end` (pattern-generalization self-assessment). These are TypeScript ports of the Claude `SessionStart` / `UserPromptSubmit` / `Stop` Python hook scripts.
- **A vendored goc engine inside the npm payload** — the same byte-for-byte mirror of `goc/` used by `claude-plugin/`, enforced by the `sync-plugin-assets` pre-commit hook.

### Prerequisites

The only host prerequisite is `python3` (3.10+) on PATH. No `uv` and no separate `pipx install game-of-cards` step are required — the engine is bundled.

### Install from ClawHub (consumers)

```sh
openclaw skills install game-of-cards
```

The same artifact is published to npm as `game-of-cards`; consumers that prefer npm can add it via OpenClaw's plugin loading mechanism (see <https://docs.openclaw.ai/plugins>).

### Install the plugin (local development)

Clone or check out this repository, then point OpenClaw at the local `openclaw-plugin/` directory per OpenClaw's local-plugin docs. The plugin's TypeScript entry point (`openclaw-plugin/index.ts`) is bundled with esbuild on `prepublishOnly`; for local development the bundled `dist/index.js` is checked in so the plugin is loadable without a build step.

### Known limitation: subagent tool projection

OpenClaw (≤ 2026.5.6) does not project the plugin's registered `goc` tool to spawned subagents — the plugin-tool allowlist ignores `tools.subagents.tools.alsoAllow`. Main sessions are unaffected; subagent flows degrade by surfacing the tool as unavailable. Upstream tracker: <https://github.com/openclaw/openclaw/pull/51388>. Workaround guidance lives in the plugin README.

## Migrating a legacy deck layout

Versions before 0.0.4 stored the deck under `deck/` at the project root. From 0.0.4 onward the deck lives under `.game-of-cards/deck/`. Both layouts work for single-tree repos, but **if both trees exist at the same time, `goc` will refuse to operate** — any command other than `goc migrate` exits with an error naming both paths.

### Why dual-tree is fatal

Two deck trees cause silent drift: a stale `goc` binary (installed globally as 0.0.3) writes to `deck/`; the local `uv run goc` (0.0.4) writes to `.game-of-cards/deck/`. Both validate independently. The divergence is invisible until a human diffs the two trees. This happened in practice — 12 hours of parallel writes in May 2026, reconciled in commit `004756d`.

### How to recover

```bash
goc migrate          # interactive — asks for confirmation before removing legacy tree
goc migrate --yes    # non-interactive
goc migrate --dry-run  # preview what would change
```

`goc migrate` inspects both trees, refuses if the same card has different content in each (drift), migrates legacy-only cards to canonical, then removes `deck/`. After a clean migration, `goc validate` confirms integrity.

If the same card appears in both trees with differing content, resolve the drift manually:

1. Decide which version is authoritative.
2. Copy the authoritative file into `.game-of-cards/deck/<card>/README.md`.
3. Re-run `goc migrate`.

If you prefer to delete the stale tree directly: `rm -rf deck/` removes the legacy path; `rm -rf .game-of-cards/deck/` removes the canonical path. Only remove the tree you are certain is fully superseded.

## Daily commands

```bash
goc
goc --board
goc -v --status all
goc new rename-the-button-to-export
goc status rename-the-button-to-export active
goc done rename-the-button-to-export
goc validate
```

Common verbs:

| Command | Purpose |
|---|---|
| `goc` | Show the open queue, sorted by leverage. |
| `goc --board` | Show a kanban board by status. |
| `goc new <title>` | Create a card under the nearest ancestor's `.game-of-cards/deck/<title>/`; requires a prior `goc install`. |
| `goc status <title> <state>` | Move a card through `open`, `active`, `blocked`, `disproved`, or `superseded`. |
| `goc decide <title> --decision X --because Y` | Record a human decision and lower the card gate. |
| `goc done <title>` | Close a card after every Definition-of-Done checkbox is ticked. |
| `goc validate` | Validate card frontmatter and schema constraints. |
| `goc install` | Install the methodology into the current repo. |
| `goc upgrade` | Re-sync generated templates in an existing install. |
| `goc migrate` | Merge legacy `deck/` into `.game-of-cards/deck/` and remove the stale tree. |

Run `goc --help` or `goc <command> --help` for the full CLI surface.

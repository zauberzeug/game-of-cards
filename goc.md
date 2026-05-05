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

- `deck/`
- `.game-of-cards/`
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

- **Ask your coding agent.** Say "expand the deck" (or "find issues to file as cards"). This triggers the `extend-deck` skill, which audits the repo for previously-undocumented defects, doc drift, missing tests, or architectural smells, and files each finding as a card via `goc new`. Re-invoke until the queue is the size you want.
- **By hand.** `goc new "rename the export button"` scaffolds a single card with valid frontmatter and a placeholder Definition of Done that `goc done` will refuse to close until you fill it in.

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

- **11 GoC skills** (same as `goc install --agents claude`) — auto-discoverable by Claude Code when the plugin is loaded.
- **SessionStart hook** — prints an active-card reminder at session start.
- **UserPromptSubmit hook** — detects work-initiating prompts and injects a deck-first reminder.

Skills and hook scripts are **symlinks** into `goc/templates/`, so the plugin and the repo-local harness always share the same source. No third copy exists.

### Prerequisites

The plugin shells to the `goc` CLI; install it first:

```bash
uv tool install game-of-cards   # or: pipx install game-of-cards
```

The plugin does not carry a minimum version check itself, but features added in later releases require matching `goc` builds.

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

### Known limitation: dynamic skill content

Skills use `!`.claude/skills/_goc-bootstrap.sh`` inline shell injections for dynamic context (queue listings, card details). When used via the plugin without a repo-local harness, that path does not exist and the injection produces an error message instead of card data. Claude handles this gracefully by working from its static instructions, but the live queue view in skills is absent.

For full dynamic feature support, either:
- Keep the repo-local harness installed alongside the plugin, or
- Copy `_goc-bootstrap.sh` from the plugin's skills to `.claude/skills/_goc-bootstrap.sh`.

A future release will fix the bootstrap path to use `${CLAUDE_SKILL_DIR}` so the plugin is fully self-contained.

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
| `goc new <title>` | Create a card under `deck/<title>/`. |
| `goc status <title> <state>` | Move a card through `open`, `active`, `blocked`, `disproved`, or `superseded`. |
| `goc decide <title> --decision X --because Y` | Record a human decision and lower the card gate. |
| `goc done <title>` | Close a card after every Definition-of-Done checkbox is ticked. |
| `goc validate` | Validate card frontmatter and schema constraints. |
| `goc install` | Install the methodology into the current repo. |
| `goc upgrade` | Re-sync generated templates in an existing install. |

Run `goc --help` or `goc <command> --help` for the full CLI surface.

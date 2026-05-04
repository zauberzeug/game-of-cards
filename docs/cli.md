# Game of Cards CLI

This is the command-level reference for the `goc` implementation. The methodology is described in the main README.

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

## Upgrade an install

After upgrading the machine-wide `goc` command, refresh generated files in a repo:

```bash
goc upgrade
goc upgrade --agents claude,codex
```

Generated guidance blocks are marker-bounded so user-authored content outside the markers is preserved.

## Daily commands

```bash
goc
goc --board
goc -v --status all
goc new "rename the button to Export"
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

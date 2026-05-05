# Game of Cards

Agile in the age of AI agents: Game of Cards is a repo-native agile methodology for turning work into durable, inspectable cards that humans and coding agents can share.

It is implemented as the `goc` command-line interface (CLI). It keeps your project's backlog as a folder of markdown files inside your repo. Each item is a *card* — a directory under `deck/` with a frontmatter header, a body, and a checklist that decides when it's done.

That's it. The rest of this README is why that turns out to be a useful shape.

## The agile thinking behind it

Three ideas from the 1990s, none of them ours, all still in use:

- **One card, one thing** — XP, Beck 1999. Small enough to fit on an index card. Enough context that anyone, or anything, can pick it up.
- **Definition of Done** — Scrum, Sutherland & Schwaber. A card isn't closed because someone said so. It's closed because a checklist is satisfied.
- **Status, not location** — Kanban, Anderson, after Toyota. A card stays at `deck/<title>/` while it moves through *open → active → done*. Cross-references don't break.

The argument for taking these seriously *now* is that AI coding agents are a harder handoff problem than the human teams those ideas were built for. Agents read the full backlog every session, re-derive context from scratch, and never remember yesterday. A card with a stable URL, a machine-checkable closure contract, and a self-contained body stops being "discipline" and starts being how the agent finds its bearings. The 1990s primitives were right; AI agents make their handoff value more obvious.

It works without any of that, too. `goc new "rename the button"`, `goc` to see what's open, `goc done rename-the-button` to close it. No AI required. The deck is just markdown files; you read, write, edit, and revert them with the same git you already use.

## Where it fits

The current agent-development ecosystem is real and useful. [Spec Kit](https://github.com/github/spec-kit) gives spec-driven development templates and bootstrapping. [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) brings AI-driven agile workflows and specialized agent roles. [Agent OS](https://github.com/buildermethods/agent-os) captures project standards and specs. [Ruler](https://github.com/intellectronica/ruler) distributes one instruction set to many agent config files. [AGENTS.md](https://agents.md/) is the shared markdown guidance format many agents read.

Game of Cards is narrower than those. It gives a repo-local backlog lifecycle: stable card paths, explicit status and gate fields, append-only logs, and a Definition of Done that the CLI refuses to close while unchecked boxes remain.

That means it can sit underneath other tools. It does not choose your planning method, author a PRD, pick personas, or orchestrate a swarm. It gives humans and agents a durable place to put work and a mechanical rule for when that work is actually done.

## Try it

If you already have a coding agent in the repo, start there:

> Install Game of Cards (https://github.com/zauberzeug/game-of-cards) in this repo, then create a first card for the next small improvement.

The agent can then install `goc`, run `goc install`, and use the generated guidance and skills for card operations. The manual equivalent is:

```bash
# Install the goc command once, using a Python app installer you already trust.
uv tool install game-of-cards
# or
pipx install game-of-cards

# Then, inside each repo:
cd any-repo
goc install
```

Prefer `uv tool install` if `uv` is already standard on your machine; prefer `pipx` if you use the PyPA application-installer path. Plain `pip install` works inside an environment, but it is the least clear global-app story because scripts and dependencies share that environment.

The cost of trying is low. `goc install` adds files; it doesn't take any away.
If you decide it isn't for you, remove the generated files and revert the
marker-bounded guidance blocks.

Once it is installed, talk to your coding agent:

- "create a card for renaming the export button"
- "implement the highest-leverage open card"
- "what's open in the deck?"

The agent guidance and skills call `goc` behind the scenes. If you want to
inspect or debug that engine directly, use the CLI:

```bash
goc                                # show what's open, sorted by leverage
goc validate                       # check every card's frontmatter against the schema
goc new "rename the button to Export"
goc done rename-the-button-to-export
```

For install flags, upgrades, and the command reference, see the [CLI guide](docs/cli.md).

## Agent harnesses

Install output is split into three layers:

- **Project state** — `deck/`, `.game-of-cards/` — always written. This is
  the methodology's durable state; no agent runtime required.
- **Guidance** — `AGENTS.md`, `.pre-commit-config.yaml` — written by default,
  readable by any agent that follows `AGENTS.md` conventions.
- **Runtime affordances** — skills, hooks, and agent-specific guidance files
  — written only when an agent harness is selected.

Harness selection controls which runtime affordances are installed:

- `--agents claude` writes `.claude/skills/`, `.claude/hooks/user-prompt-submit-goc.py`, and `CLAUDE.md`.
- `--agents codex` writes Codex-readable skills under `.codex/skills/`, without Claude-only hooks.
- `--no-harness` installs project state and guidance only — no skills, no hooks, no agent-specific files. Useful for repos that drive GoC purely through the `goc` CLI or that use a plugin-provided harness.

Detection is intentionally simple: Claude markers such as `CLAUDE.md` or
`.claude/` select the Claude harness, Codex markers such as `AGENTS.md` or
`.codex/` select the Codex harness, and both marker families install both
harnesses. Explicit `--agents`, `--claude`, `--codex`, and `--no-harness`
flags override detection for scripted installs.

OpenCode is a free path: it already reads `.claude/skills/`, so `goc install --agents claude` gives OpenCode the skill files without a separate OpenCode shim. The Claude `UserPromptSubmit` hook is not part of that compatibility path; hooks remain Claude Code-specific.

To add another agent, file an issue or PR that adds `goc/templates/agents/<agent>/manifest.json`, any renderer support needed for that agent's file format, and installer tests covering `goc install --agents <agent>` plus `goc upgrade --agents <agent>`. OpenCLAW is deferred until a downstream repo needs native OpenCLAW guidance.

## What you get

- A `deck/<title>/` directory per card: frontmatter-validated `README.md`, append-only `log.md`, and stable git paths that survive status changes.
- A `.game-of-cards/` per-repo config layer for project-specific content and workflow hooks. The convention — directory layout, file format, hook-point catalog — is documented in [`.game-of-cards/README.md`](goc/templates/game_of_cards/README.md), which `goc install` ships into every consuming repo.
- An `AGENTS.md` block for Codex and other editors that read shared repo guidance.
- Agent skill files (`scan-deck`, `next-card`, `create-card`, `advance-card`, `decide-card`, `finish-card`, `improve-deck`, `extend-deck`, `pull-card`, `card-schema`, `deck`) so Claude or Codex can turn user prompts into card operations.
- A `goc` CLI — 13 verbs covering create, browse, advance, decide, close, validate, install, and upgrade — for humans, scripts, hooks, and agent skills.
- A schema validator suitable for pre-commit and CI.

## Status

Brand new alpha: only a few days of implementation, no external users yet,
and plenty of rough edges that are unknown until someone tries it on a fresh
project. Bring expectations to match.

The right way to find out if it's for you is to install it, point it at a side project, and see whether it stays out of your way for a week. If it does, you'll keep it. If it doesn't, you've spent five minutes.

## Contributing

When working from a checkout of this repo, use the repo-local form so you run the checked-out code instead of any globally installed `goc`:

```bash
uv run goc install --agents codex
```

This repo uses Game of Cards to track its own work. The `deck/` directory is the backlog; each card is a directory under that with a frontmatter-validated `README.md` and an append-only `log.md`. If you want to contribute to existing work, pick an open card and update that card as part of your change. If you want to propose new work, run `uv run goc new "card title"` to scaffold the card directory.

We are open to contributions of all sizes, from fixing typos to implementing new features. If you're not sure where to start, ask your LLM to check the open cards in `deck/` and see if anything catches your eye. If you want to propose a new feature or improvement, feel free to file an issue or PR; we will convert issues into cards quickly.

## License

MIT — Copyright (c) 2026 Zauberzeug GmbH. See [`LICENSE`](LICENSE).

# Game of Cards

A small command-line tool that keeps your project's to-do list as a folder of markdown files inside your repo. Each item is a *card* — a directory under `deck/` with a frontmatter header, a body, and a checklist that decides when it's done.

That's it. The rest of this README is why that turns out to be a useful shape.

## The agile thinking behind it

Three ideas from the 1990s, none of them ours, all still in use:

- **One card, one thing** — XP, Beck 1999. Small enough to fit on an index card. Enough context that anyone, or anything, can pick it up.
- **Definition of Done** — Scrum, Sutherland & Schwaber. A card isn't closed because someone said so. It's closed because a checklist is satisfied.
- **Status, not location** — Kanban, Anderson, after Toyota. A card stays at `deck/<title>/` while it moves through *open → active → done*. Cross-references don't break.

The argument for taking these seriously *now* is that AI coding agents are a much harder handoff problem than the human teams those ideas were built for. Agents read the full backlog every session, re-derive context from scratch, and never remember yesterday. A card with a stable URL, a machine-checkable closure contract, and a self-contained body stops being "discipline" and starts being how the agent finds its bearings. The 1990s primitives were right for a different reason than the 1990s knew about.

It works without any of that, too. `goc new "rename the button"`, `goc` to see what's open, `goc done rename-the-button` to close it. No AI required. The deck is just markdown files; you read, write, edit, and revert them with the same git you already use.

## What it is, and what it isn't

Game of Cards is a *substrate*. The CLI, the schema, the on-disk card layout, the validator — that's all it ships. There's no preferred LLM, no proprietary state, no mandatory workflow.

What sits on top is up to you. Claude Code skills come bundled as the reference harness; any editor that reads `AGENTS.md` (Codex, Cursor, OpenCode, Copilot, Aider) can drive the same deck. So can a shell script. So can your hands.

This is *not* another methodology framework. Spec-Kit ships templates. BMAD ships personas. Ruler ships rule fan-out. claude-flow ships swarm orchestration. Each sits on top of a substrate that the consuming team has to provide. Game of Cards *provides* one.

## Try it

```bash
uv tool install game-of-cards     # one-time, machine-wide
cd any-repo
goc install                       # default: Claude Code harness plus shared AGENTS.md guidance
goc install --agents claude        # explicit Claude Code harness
goc install --codex               # Codex harness only: deck/, AGENTS.md, .game-of-cards/, .codex/skills/
goc install --agents codex        # same as --codex
```

When working from a checkout of this repo, use the repo-local form:

```bash
uv run goc install --agents codex
```

The cost of trying is low. `goc install` adds files; it doesn't take any away. If you decide it isn't for you, `rm -rf deck/` and revert the two README sections — you're back where you started.

A few things you can do once it's installed:

```bash
goc new "rename the button to Export"
goc                                # show what's open, sorted by leverage
goc validate                       # check every card's frontmatter against the schema
goc done rename-the-button-to-export
```

If you're using Claude Code or any `AGENTS.md`-aware editor, you can also just talk to it: *"rename the button to Export."* The deck reflects either flow on the same on-disk state.

## Agent harnesses

The v1 installed harness set is intentionally small:

- `claude` is the no-flag default. It writes `.claude/skills/`, `.claude/hooks/user-prompt-submit-goc.py`, `CLAUDE.md`, and the shared `AGENTS.md` guidance.
- `codex` writes Codex-readable skills under `.codex/skills/` plus the shared `AGENTS.md` guidance, without Claude-only hooks.

OpenCode is a free path: it already reads `.claude/skills/`, so `goc install --agents claude` gives OpenCode the skill files without a separate OpenCode shim. The Claude `UserPromptSubmit` hook is not part of that compatibility path; hooks remain Claude Code-specific.

To add another agent, file an issue or PR that adds `goc/templates/agents/<agent>/manifest.json`, any renderer support needed for that agent's file format, and installer tests covering `goc install --agents <agent>` plus `goc upgrade --agents <agent>`. OpenCLAW is deferred until a downstream repo needs native OpenCLAW guidance.

## What you get

- A `goc` CLI — 13 verbs covering create, browse, advance, decide, close, validate, and install.
- A `deck/<title>/` directory per card: frontmatter-validated `README.md`, append-only `log.md`.
- A schema validator suitable for pre-commit and CI.
- A starter set of GoC skills (`scan-deck`, `next-card`, `create-card`, `advance-card`, `decide-card`, `finish-card`, `improve-deck`, `extend-deck`, `pull-card`, `card-schema`, `deck`) that turn the CLI into an autonomous workflow when you want one.
- Harness install targets for `claude` and `codex`. `claude` is the no-flag default and writes `.claude/skills/`, `.claude/hooks/user-prompt-submit-goc.py`, and the Claude-specific `CLAUDE.md` block; `codex` writes Codex-readable skills and AGENTS.md-centered guidance without Claude-only prompt hooks.
- An `AGENTS.md` block for Codex and other editors that aren't Claude Code.
- A `.game-of-cards/` per-repo config layer for project-specific content and workflow hooks. The convention — directory layout, file format, hook-point catalog — is documented in [`.game-of-cards/README.md`](goc/templates/game_of_cards/README.md), which `goc install` ships into every consuming repo.

## Status

Brand new. This is `0.0.1` — only a few days of implementation, no external users yet, plenty of rough edges that are unknown until someone tries it on a fresh project. Bring expectations to match.

The right way to find out if it's for you is to install it, point it at a side project, and see whether it stays out of your way for a week. If it does, you'll keep it. If it doesn't, you've spent five minutes.

## License

MIT — Copyright (c) 2026 Zauberzeug GmbH. See [`LICENSE`](LICENSE).

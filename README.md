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
goc install                       # auto-detect Claude/Codex markers; no marker defaults to Claude
goc install --agents claude        # explicit Claude Code harness
goc install --agents codex         # explicit Codex harness
goc install --agents claude,codex  # both harnesses
```

When working from a checkout of this repo, use the repo-local form:

```bash
uv run goc install --agents codex
```

Detection is intentionally simple: Claude markers such as `CLAUDE.md` or
`.claude/` select the Claude harness, Codex markers such as `AGENTS.md` or
`.codex/` select the Codex harness, and both marker families install both
harnesses. Explicit `--agents`, `--claude`, and `--codex` flags override
detection for scripted installs.

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

## Agent harnesses

Every install writes the shared substrate: `deck/`, `.game-of-cards/`,
`AGENTS.md`, and `.pre-commit-config.yaml`. Harness selection controls the
agent-specific files layered on top:

- `claude` writes `.claude/skills/`, `.claude/hooks/user-prompt-submit-goc.py`, and `CLAUDE.md`.
- `codex` writes Codex-readable skills under `.codex/skills/`, without Claude-only hooks.

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

## License

MIT — Copyright (c) 2026 Zauberzeug GmbH. See [`LICENSE`](LICENSE).

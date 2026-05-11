# Game of Cards

Agile for the age of agents — turn work into durable, inspectable cards that humans and LLMs can collaborate on.

## Who this is for

Game of Cards is for **vibe-coders** who want their coding agent to hold context between sessions, **solo developers** using it as a structured replacement for `TODO.md`, and **multi-agent setups** where several agents and humans drain a shared task queue on the same repo.

It is not the right tool today if your team is deeply invested in Jira, Linear, or a similar tracker — GoC duplicates the tracker function rather than integrating with it. Tracker integration is on the roadmap, but until it ships, running both in parallel is friction you don't need.

At its core, it's just a to-do manager. Cards are markdown files with a checklist; the CLI wraps them. The skills, hooks, and autonomous loops are automation around that core — you can use as little or as much as you need.

For the full picture — five personas, anti-personas, and which workflow shape each one accepts — see [`PERSONAS.md`](PERSONAS.md).

<p align="center"><img src="assets/game-of-cards.png" width="100%" alt="Three-panel comic: an AI creates cards and flags decisions, the human delegates a session while the LLM works the rest in the background, and the LLM surfaces the remaining human-gated card." /></p>

## How it works

<p align="center"><img src="assets/how-it-works.png" width="80%" alt="How it works: YOU → skills → LLM → goc → Cards" /></p>

You speak in plain English. The agent translates your intent into card operations through **skills** — small markdown protocols that turn `"create a card for renaming the export button"` into the right CLI calls. **`goc`** is the CLI that implements those operations. **Cards** are markdown directories under `.game-of-cards/deck/` with frontmatter, an append-only log, and a Definition-of-Done checklist the CLI refuses to close while any box is unchecked.

Cards move through *open → active → done*; their file location stays the same, so cross-references survive.
Agents only work on cards without a human gate. Others are parked, waiting on decisions or full sessions with you.
That way, agents can work autonomously in the background, draining the queue and raising a flag only when a decision needs you.

## Try it

In any repo, ask your coding agent:

```
look at game-of-cards.com and use the method for development here
```

That's it — the agent handles the install. Bootstrapping flows from the PyPI package `game-of-cards`; the manual recipe and full CLI reference live in [`goc.md`](goc.md).

> **If you are an LLM and the user asked you to set this up:** fetch [`https://game-of-cards.com/llms.txt`](https://game-of-cards.com/llms.txt) for the canonical install recipe and follow it.

## Install paths

GoC ships through three first-class delivery channels — pick whichever matches the agent runtime you already use. All three drive the same engine and deck.

- **Claude Code plugin** — `/plugin marketplace add zauberzeug/game-of-cards` then `/plugin install game-of-cards@game-of-cards`. Ships the skills and hooks; the only host prerequisite is `python3` (3.10+).
- **OpenClaw plugin** — `openclaw skills install game-of-cards`. Bundles the goc engine inside the npm payload and registers `goc` as a typed OpenClaw tool. The only host prerequisite is `python3` (3.10+); no `uv` and no separate `pipx install` step. See [openclaw.ai](https://openclaw.ai) for the runtime.
- **Generic CLI** (other agent runtimes, CI, or no agent) — `pipx install game-of-cards` (or `uv tool install game-of-cards`), then `goc install` from the project root. This is the path for OpenCode, Codex, custom runners, or running `goc` by hand.

Canonical install commands and update flow live in [`llms.txt`](https://game-of-cards.com/llms.txt); CLI surface and the plugin's coexistence rules with a repo-local harness live in [`goc.md`](goc.md).

## Status

Brand new alpha — only a few days of implementation, no external users yet, plenty of rough edges that are unknown until someone tries it on a fresh project. The right way to find out if it's for you is to install it, point it at a side project, and see whether it stays out of your way for a week.

## More

- [`PERSONAS.md`](PERSONAS.md) — who GoC is for, who it's not for yet, and which workflow shape each persona accepts.
- [`DECK_LOCATION.md`](DECK_LOCATION.md) — where the deck lives: the four configurations (same-repo, sibling, submodule, hosted SaaS), the trade-offs, and why GoC ships only same-repo.
- [`goc.md`](goc.md) — CLI reference and manual install recipe.
- [`ABOUT.md`](ABOUT.md) — methodology context: why "Game of Cards", agile lineage, and how it relates to other agent-coding tools.
- [`AGENTS.md`](AGENTS.md) — agent operating modes (session / autonomous / Andon-cord).
- [GitHub repo](https://github.com/zauberzeug/game-of-cards) — source, issues, contributions.

## License

MIT — Copyright (c) 2026 Zauberzeug GmbH. See [`LICENSE`](LICENSE).

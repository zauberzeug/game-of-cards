# Game of Cards

**Agile in the age of AI agents.**

The original agile artifacts — the card on a wall, the standup, the retro — were designed for humans who needed lightweight handoffs. AI agents are a more aggressive handoff-stress-test: they read the full backlog every session, re-derive context from scratch, and never remember yesterday. That makes machine-checkable DoDs and slug-as-URL more load-bearing now than they were in 2001 — XP got the right primitives for the wrong reason.

The Game-of-Thrones cadence is the part XP, Scrum, and Kanban don't even attempt to name: the emergent, uncontrollable quality of work in a human + AI-agent swarm. You don't drive the swarm; events surface, you respond. That's the 2020s addition to the agile canon.

## Substrate, not framework

Spec-Kit ships templates. BMAD ships personas. Ruler ships rule fan-out. claude-flow ships swarm orchestration. Each of those sits *on top of* a substrate that you, the consuming team, have to provide.

Game of Cards ships the substrate. The CLI, the schema, the on-disk story-card layout, the lifecycle enforcement (DoD-checked closure, Andon-cord escalation, additive Bellman value math across the full card graph, status-as-soft-lock for parallel agents) — that's the layer underneath. The harness on top is interchangeable: Claude Code skills are shipped here as the reference harness, but Codex, Cursor, OpenCode, Copilot, and Aider all read [`AGENTS.md`](https://agents.md), so any of them — or all of them, in parallel — can drive the same cards.

## Install

```bash
uv tool install game-of-cards
goc --version
```

The PyPI distribution is published as `game-of-cards`; the import name and console script are `goc` (the *pyyaml* pattern: long descriptive distribution name, terse working name everywhere else).

## What you get

- **`goc` CLI** — manages a `deck/<title>/` directory of story-cards (frontmatter-driven, schema-validated). 13 verbs: `new`, `done`, `move`, `validate`, `triage`, `show`, `status`, `advance`, `unadvance`, `decide`, `attest`, `quality-pass`, `install`. This is the substrate.
- **Claude Code skill set** — `scan-deck`, `next-card`, `create-card`, `advance-card`, `decide-card`, `finish-card`, `improve-deck`, `extend-deck`, `pull-card`, `card-schema`, `deck`. Turns the substrate into an autonomous workflow under Claude Code. One harness, shipped.
- **`AGENTS.md` block + `.game-of-cards/` config layer** — the Linux-Foundation-stewarded shared-substrate convention; agent runtimes other than Claude Code see the same workflow without Claude-specific bindings. Project-local content stubs and workflow hooks slot in via `.game-of-cards/`.

## Status

Pre-`0.1.0` — extracted from the [phasor-agents](https://github.com/zauberzeug/phasor-agents) monorepo, where the methodology was developed in production over six months alongside a research codebase that needed every primitive earlier than it would have been built standalone.

## License

MIT — Copyright (c) 2026 Zauberzeug GmbH. See `LICENSE`.

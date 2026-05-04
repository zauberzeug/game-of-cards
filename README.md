# Game of Cards

XP-style story-card kanban methodology framework with DoD enforcement, Andon-cord, additive Bellman value math; CLI + Claude Code skills.

```bash
uv tool install game-of-cards
goc --version
```

The PyPI distribution is published as `game-of-cards`; the import name and console script are `goc` (the *pyyaml* pattern: long descriptive distribution name, terse working name everywhere else).

## What you get

- A `goc` CLI for managing a `deck/<title>/` directory of story-cards (frontmatter-driven, schema-validated).
- Claude Code skills (`scan-deck`, `next-card`, `create-card`, `advance-card`, `decide-card`, `finish-card`, `improve-deck`, `extend-deck`, `pull-card`, `card-schema`, `deck`) that turn the CLI into an autonomous workflow.
- A `.game-of-cards/` per-repo config layer for project-local content + workflow hooks.

## Status

Pre-`0.1.0` — extracted from the [phasor-agents](https://github.com/zauberzeug/phasor-agents) monorepo, where the methodology was developed in production over six months.

## License

MIT — Copyright (c) 2026 Zauberzeug GmbH. See `LICENSE`.

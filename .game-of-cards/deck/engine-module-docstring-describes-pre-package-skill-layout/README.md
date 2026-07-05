---
title: engine-module-docstring-describes-pre-package-skill-layout
summary: "The `goc/engine.py` module docstring still describes the pre-package era: it names the file `deck.py`, says it lives inside the deck skill, instructs running `.claude/skills/deck/deck.py`, locates the schema at `.claude/skills/card-schema/schema.yaml`, and puts cards at a project-root `deck/` directory — all contradicted by the code directly below it."
status: done
stage: null
contribution: low
created: "2026-07-05T01:33:09Z"
closed_at: "2026-07-05T01:44:39Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [x] MECHANICAL: `goc/engine.py` module docstring names the real module (`goc/engine.py`, `goc` CLI entry point), the real schema path (`goc/schema.yaml` package data), and the real deck location (`.game-of-cards/deck/` with legacy `deck/` fallback)
  - [x] MECHANICAL: plugin mirrors regenerated (`sync-plugin-assets` pre-commit) so the corrected header ships in all three payloads
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# `goc/engine.py` module docstring describes the pre-package `deck.py` skill layout

## Location

`goc/engine.py:1-12` (the module docstring).

## What's broken

The first thing a cold reader of the ~6,300-line core module sees is a
header from the pre-package era:

```python
"""deck.py — deck CLI; lives inside the deck skill.

Computes filtered kanban-style views over `deck/<title>/README.md` frontmatter.
The deck is the project's card-tracking surface — one card per work item, with
status (open/active/blocked/done/disproved/superseded) on a kanban board.

Run via `uv run python .claude/skills/deck/deck.py …` per project's `uv run`
discipline. The schema is a YAML data file at the sibling card-schema skill:
`.claude/skills/card-schema/schema.yaml`. Cards (the data instances) live at
the project-root `deck/` directory; only the methodology (CLI + schema +
skill bodies) lives under `.claude/skills/`.
"""
```

Contradicted by the code directly below:

- The file is `goc/engine.py`, installed as a package and invoked via the
  `goc = "goc.cli:main"` entry point (`pyproject.toml`) — there is no
  `.claude/skills/deck/deck.py`.
- The schema is package data: `SCHEMA_FILE = PACKAGE_DIR / "schema.yaml"`
  (`goc/engine.py:124`).
- Cards live at `.game-of-cards/deck/` with a legacy `deck/` fallback and
  dual-tree conflict detection (`goc/engine.py:97-119`).

## Why it matters

The header ships in every wheel and in all three plugin payload mirrors
(`claude-plugin/goc/`, `codex-plugin/goc/`, `openclaw-plugin/goc/`). A cold
reader — or an agent grepping for orientation — is pointed at a file path,
a schema path, and a deck location that do not exist.

## Fix

Rewrite the docstring to name the real module, entry point, schema path,
and deck location. Keep it short; the details live in AGENTS.md. Mirrors
regenerate automatically via the `sync-plugin-assets` pre-commit hook.

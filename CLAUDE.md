# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## This repo *is* `goc` — and it dogfoods itself

The package under `goc/` is the Game of Cards CLI; the assets under
`.claude/`, `.game-of-cards/`, and the `<!-- BEGIN GOC -->` block below
are this repo's own *consumer* copy of what `goc install` ships. The
deck under `deck/` is real work for the tool itself (cards prefixed
`goc-*`). Behavior you observe here is the behavior shipped to
consumers — there is no separate "framework" repo.

## Common commands

```bash
uv sync                            # install dev environment
uv pip install --system -e .       # editable install (what CI does)
uv run goc --help                  # exercise the CLI from source
uv run goc validate                # check every card's frontmatter
uv build                           # produce wheel + sdist in dist/
pre-commit run --all-files         # runs `goc validate` (the only hook)
```

No pytest suite exists yet. `.github/workflows/ci.yml` is a
build + console-script + `goc validate` smoke matrix on Python
3.10–3.13; the validation step is what gates card-frontmatter drift.

Releases: push tag `vX.Y.Z` whose value matches `pyproject.toml`'s
`version` (the workflow verifies the match before publishing). PyPI
auth is OIDC trusted publishing — no tokens in the repo.

## Code architecture

The Python package is intentionally small (4 source files):

- **`goc/cli.py`** — thin Click entry point. Imports the engine's Click
  group, bolts on `install` + `upgrade` from `install.py`, and adds
  `--version`. Wired as `goc = "goc.cli:main"` in `pyproject.toml`.
- **`goc/engine.py`** — ~1.8 kLOC, the bulk of the tool: frontmatter
  parser, schema loader, card loader, validator, value/edge graph,
  table/board renderers, and every verb except install/upgrade
  (`new`, `status`, `done`, `attest`, `decide`, `advance`, `unadvance`,
  `move`, `triage`, `show`, `quality-pass`, `validate`).
- **`goc/install.py`** — `install` and `upgrade` commands. Reads
  templates via `importlib.resources` so it works from a wheel.
- **`goc/schema.yaml`** — single source of truth for card frontmatter
  (loaded by `engine.load_schema()`; inlined into the `card-schema`
  skill body at install time).

`engine.py` resolves `DECK_DIR = Path.cwd() / "deck"`, so running `goc`
from the repo root operates on the repo's own deck.

### Templates ship as package data

`goc/templates/` is bundled into the wheel and is the source of truth
for everything `goc install` writes into a consuming repo:

| Template path | Installed to |
|---|---|
| `templates/skills/<verb>/` | `<repo>/.claude/skills/<verb>/` |
| `templates/hooks/user-prompt-submit.py` | `<repo>/.claude/hooks/user-prompt-submit-goc.py` |
| `templates/game_of_cards/` | `<repo>/.game-of-cards/` |
| `templates/AGENTS_GOC.md`, `templates/CLAUDE_GOC.md` | merged into AGENTS.md / CLAUDE.md |

### Skill and config files have two copies — edit the template

Because this repo dogfoods itself, every file under `.claude/skills/`,
`.claude/hooks/user-prompt-submit-goc.py`, and `.game-of-cards/` is a
*consumer copy* of the corresponding file under `goc/templates/`. The
next `goc upgrade` overwrites the consumer copy from the template.
**When editing skill bodies, hook scripts, or per-repo config stubs,
edit `goc/templates/...` and re-run `goc upgrade`** (or edit both
copies in lockstep). Editing only `.claude/skills/...` is silently
lost on the next upgrade.

### Marker-bounded merge for AGENTS.md / CLAUDE.md

`install._append_marker_block` rewrites only the content between
`<!-- BEGIN GOC v… -->` and `<!-- END GOC -->`. Content above or below
those markers is preserved across `goc install` / `goc upgrade`. This
section is therefore safe to extend; the block below it is generated
from `goc/templates/CLAUDE_GOC.md` and round-trips cleanly.

<!-- BEGIN GOC v0.0.3 -->
## Game of Cards — Claude Code specifics

The shared briefing is in [AGENTS.md](AGENTS.md) — three operating
modes (session / autonomous / Andon-cord), the `goc` CLI verb table,
and the deck philosophy apply to every runtime.

What's **Claude-specific** and lives only here:

### Skill surface (the 11 verbs as `Skill(...)`)

Skills under `.claude/skills/` are **optional runtime affordances** installed
by `goc install --agents claude`. The core methodology works with just the
`goc` CLI; skills are convenience wrappers that surface the same verbs as
Claude Code's `Skill(...)` primitive. Repos that use GoC without a checked-in
Claude harness invoke the CLI directly via AGENTS.md guidance.

When installed, the 11 skills are:

- **Browse**: `Skill(scan-deck)` (triage default + filtered views + decision Q&A); `Skill(next-card)` (auto-pick highest-leverage gate=none card).
- **File new**: `Skill(create-card)` (scaffold frontmatter + DoD).
- **Advance**: `Skill(advance-card)` (status flip), `Skill(finish-card)` (close + DoD enforcement + commit).
- **Decide (human handoff)**: `Skill(decide-card)` (lowers gate decision/session → none).
- **Hygiene**: `Skill(improve-deck)` (retag stale, prune parks); `Skill(extend-deck)` (hunt new defects).
- **Reference**: `Skill(card-schema)` (required/optional fields, enums, canonical tags).
- **Autonomous**: `Skill(pull-card)` (one round of pull → claim → work → close → commit).
- **Overview**: `Skill(deck)` (methodology front door and shared operating model).

These wrap the same `goc <verb>` CLI documented in AGENTS.md, but
expose them as Claude Code's skill primitive so they're invokable
by name and can carry richer prompt scaffolding (decision rubrics,
Andon-cord guards, etc.).

### Silent runtime via `UserPromptSubmit` hook

`.claude/hooks/user-prompt-submit-goc.py` is an **optional** Claude-Code-only
hook installed by `goc install --agents claude`. It detects work-initiating
prompts and injects a deck-first reminder into Claude's view of the user
message. The reminder runs the silent pipeline
(`scan-deck → create-card → advance-card → implement → finish-card`)
without announcing card operations to the user. Vibe coders see code,
not bookkeeping.

The hook is not required for GoC to work — it is a convenience affordance.
Repos without it still get full GoC functionality through the `goc` CLI and
the AGENTS.md guidance. Other agent runtimes implement the same flow through
their own installed GoC skills or by invoking the CLI verbs from `AGENTS.md`.
The prompt hook remains Claude-only.
<!-- END GOC -->

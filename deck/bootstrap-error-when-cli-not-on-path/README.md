---
title: bootstrap-error-when-cli-not-on-path
summary: "When someone clones a GoC-using repo onto a machine that doesn't have `goc` installed, every skill/hook invocation will fail with cryptic shell errors (`zsh: command not found: goc` or a Python ImportError). This card adds a small wrapper script that the skills shell to instead — `.claude/skills/_goc-bootstrap.sh` — which detects the missing CLI and emits one clean line: `Game of Cards CLI not found. Install with: pipx install game-of-cards`. Same approach `npm` projects take ('npm not found' is its own helpful message, not a Python traceback). Also handles the `goc` version mismatch case (installed `goc` is older than the schema this repo expects)."
status: active
stage: null
contribution: low
created: 2026-05-03
closed_at: null
human_gate: none
advances: [ship-game-of-cards-as-cross-agent-cli]
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] `.claude/skills/_goc-bootstrap.sh` (or `.py`) wrapper exists; skills shell to it instead of `goc` directly
  - [ ] When `goc` is on PATH and version is compatible: wrapper exec's `goc "$@"` transparently (no overhead beyond one shell layer)
  - [ ] When `goc` is missing from PATH: wrapper exits with code 127 and prints exactly one line: `Game of Cards CLI not found. Install with: pipx install game-of-cards`
  - [ ] When `goc --version` reports older than `.goc-version` sentinel in `deck/`: wrapper exits with code 1 and prints: `Game of Cards CLI is older than this repo's schema (installed: X, required: Y). Run: pipx upgrade game-of-cards`
  - [ ] All 11 skill SKILL.md files updated to invoke `.claude/skills/_goc-bootstrap.sh` instead of `goc` (or `uv run python .claude/skills/deck/deck.py`) directly
  - [ ] `goc install` writes the bootstrap wrapper as part of the scaffold
  - [ ] Tested on a clean machine without `goc` installed: cloning a GoC repo and asking the agent to file a card produces the helpful install message, not a traceback
---

# Bootstrap error when `goc` is not on PATH

## Why

Sub-card of `ship-game-of-cards-as-cross-agent-cli`. This is a small UX detail with disproportionate value: it's the difference between a new user landing on a clear next step ("install this with one command") vs. landing on a Python traceback they have to decode.

Once `goc` lives on PyPI (sub-card 1) and skills/hooks shell to it (the migration in sub-card 6), the assumption is that every developer on a GoC-using repo has `goc` on PATH. That assumption breaks the moment someone clones the repo on a fresh machine. Without a good failure message, the entire methodology looks broken; with one, the user is one `pipx install` away from working.

This is the same pattern `npm` projects take — `command not found: npm` is itself a helpful message; the failure mode is fine. Python tooling traditionally produces tracebacks. We can do better with one line of shell.

## What

A thin wrapper script `.claude/skills/_goc-bootstrap.sh` (POSIX shell; portable across macOS/Linux dev machines) that the skills invoke instead of `goc` directly:

```bash
#!/bin/sh
set -e

if ! command -v goc >/dev/null 2>&1; then
    echo "Game of Cards CLI not found. Install with: pipx install game-of-cards" >&2
    exit 127
fi

# Optional version check
REQUIRED=$(cat "$(git rev-parse --show-toplevel)/deck/.goc-version" 2>/dev/null || echo "")
if [ -n "$REQUIRED" ]; then
    INSTALLED=$(goc --version 2>/dev/null | awk '{print $NF}')
    if ! goc-version-compare "$INSTALLED" ">=" "$REQUIRED"; then
        echo "Game of Cards CLI is older than this repo's schema (installed: $INSTALLED, required: $REQUIRED). Run: pipx upgrade game-of-cards" >&2
        exit 1
    fi
fi

exec goc "$@"
```

(`goc-version-compare` is either a separate helper or inline `python -c "..."`; the design choice is implementation-detail.)

Skills shell to this wrapper:

```yaml
# Before: invokes uv run python .claude/skills/deck/deck.py kanban
# After: invokes .claude/skills/_goc-bootstrap.sh kanban
```

## How

1. Author the wrapper script.
2. Update all 11 skill SKILL.md files to invoke the wrapper instead of `uv run python .claude/skills/deck/deck.py` (this aligns with the dogfood-migration card 6).
3. `goc install` writes the wrapper as part of the scaffold (it's package data alongside the skills).
4. Test on a clean Docker container or a colleague's fresh machine: clone a GoC-using repo, invoke a skill, confirm the install message lands.

## Why this is low-contribution (not medium)

- One file, ~20 lines of shell.
- Self-contained; doesn't block anything.
- The value is real (UX clarity at first-encounter) but the implementation is trivial.

## Cross-references

- Parent epic: `ship-game-of-cards-as-cross-agent-cli`
- Depends on: sub-card 1 (PyPI release exists; `pipx install game-of-cards` is the install command)
- Aligned with: sub-card 6 (dogfood migration changes skills to use the wrapper)

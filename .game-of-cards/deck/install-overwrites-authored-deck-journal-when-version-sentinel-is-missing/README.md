---
title: install-overwrites-authored-deck-journal-when-version-sentinel-is-missing
summary: "`goc install`'s only already-installed guard is the `.goc-version` sentinel, and the deck-journal write is unconditional. A real deck without the sentinel — e.g. adopted CLI-first via `goc new`, which never stamps one — is treated as a fresh target and its authored `deck/log.md` is destroyed. The upgrade planner explicitly skips `log.md` as preserve-worthy; install writes it blind."
status: open
stage: null
contribution: high
created: "2026-07-19T04:08:07Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` (which guard shape install adopts).
  - [ ] TDD: `uv run python .game-of-cards/deck/install-overwrites-authored-deck-journal-when-version-sentinel-is-missing/reproduce.py` exits zero (authored journal survives, or install refuses, per the decision).
  - [ ] TDD: regression test in `tests/test_install.py` covers `goc install` into a sentinel-less deck that has an authored `log.md`.
  - [ ] MECHANICAL: `install.py` docstring/comments state the chosen guard semantics (what counts as "already installed").
---

# `goc install` overwrites the authored deck journal when the `.goc-version` sentinel is missing

## Location

- `goc/install.py:453-461` — `_find_installed_deck_dir`: returns a hit
  only `if (new / ".goc-version").exists()` (same for the legacy tree).
- `goc/install.py:1538-1544` — the already-installed refusal, keyed
  solely on that sentinel lookup.
- `goc/install.py:1562` — the unconditional clobber:
  `(deck_dir / "log.md").write_text("# Deck Log\n\nAppend deck-level events here (sprint notes, schema bumps, etc.).\n")`
- `goc/install.py:920-921` — the upgrade planner's contrasting rule:
  `if write.path.name == "log.md": continue` (upgrade never touches the
  journal).

## What's broken

The install path decides "fresh target vs existing install" entirely
from the `.goc-version` sentinel. When a real deck exists but the
sentinel is absent, `install()` sails past the refusal and rewrites
`.game-of-cards/deck/log.md` with the pristine stub, destroying
authored journal content. This contradicts the repo's ownership
contract (AGENTS.md, `.game-of-cards/` ownership model): the engine
"never destroys authored content under `.game-of-cards/`". The
codebase already encodes that `log.md` is preserve-worthy — the
*upgrade* planner explicitly skips it (`goc/install.py:920-921`) — but
the *install* executor writes it blind. Every other surface install
touches has preservation machinery (`_sync_game_of_cards_config`
preserves diverged stubs; marker blocks are goc-owned by contract);
the deck journal is the one user-owned file written unconditionally.

## Empirical evidence

`uv run python .game-of-cards/deck/install-overwrites-authored-deck-journal-when-version-sentinel-is-missing/reproduce.py`:

```
goc install rc: 0
deck/log.md after install:
# Deck Log

Append deck-level events here (sprint notes, schema bumps, etc.).

FAIL: `goc install` overwrote the authored deck journal (sentinel-less deck was treated as a fresh target)
[exit 1]
```

## Why it matters

A sentinel-less deck is not an exotic state — it is the natural result
of CLI-first adoption, reachable through shipping verbs alone:
`goc new` scaffolds cards into `.game-of-cards/deck/` without ever
stamping `.goc-version` (verified empirically: a deck built purely via
`goc new` / `goc status` / `goc wait` has no sentinel). A user who
starts CLI-only, authors a deck-level journal per the methodology
docs, and later runs `goc install` to add the Claude/Codex harness
silently loses that journal — and the install then stamps a sentinel,
erasing the evidence that anything was wrong. Other reachable shapes:
a `.gitignore`/`export-ignore` rule that excludes the machine-state
sentinel, or backup/copy tooling that drops hidden files.

## Decision required

Three credible fix shapes:

1. **Create-only journal write** — `if not (deck_dir / "log.md").exists():`
   before the write at `goc/install.py:1562`, mirroring the upgrade
   planner's skip. Minimal, preserves current install semantics
   otherwise.
2. **Broaden already-installed detection** — treat an existing
   `.game-of-cards/deck/` directory (with any content) as "already
   installed" and refuse with the `goc upgrade` hint, sentinel or not.
   Stricter, but changes behavior for the legitimate "empty pre-created
   deck dir" case.
3. **Both** — create-only write plus a warning (and sentinel stamp)
   when a deck exists without `.goc-version`, making the CLI-first
   adoption path first-class.

Option 1 is the minimum safe fix; option 3 makes the reachability path
a supported workflow. The dry-run plan (`_plan_writes`,
`goc/install.py:866`) should reflect whichever action is chosen so the
preview stays truthful (cf. the open meta-card
[dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting](../dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting/)).

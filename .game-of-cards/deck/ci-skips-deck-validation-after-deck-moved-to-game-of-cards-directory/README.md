---
title: ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory
summary: "CI's final step guards on `if [ -d deck ]`, but the canonical deck moved to `.game-of-cards/deck/` (commit 9fa3a24). Root `deck/` no longer exists, so CI silently takes the `No deck/ directory yet — skipping validation` branch and never runs `goc validate` on the real 224-card deck. The frontmatter-drift gate that AGENTS.md calls load-bearing is dead in CI; only the local pre-commit hook still catches drift."
status: open
stage: null
contribution: high
created: "2026-05-27T00:53:41Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — the CI deck-validate step's path guard resolves to the canonical deck directory and would invoke `goc validate` on the real deck.
  - [ ] MECHANICAL: `.github/workflows/ci.yml` "Validate deck" step guards on `.game-of-cards/deck` (with legacy `deck/` fallback if desired), so `goc validate` actually runs on this repo's own deck in CI.
  - [ ] MECHANICAL: the stale `ci.yml` header comment is refreshed — it still says "All 11 skill templates" (there are 17) and refers to "the repo's own `deck/` directory" / the old scaffolding card; reword to match the `.game-of-cards/deck/` reality.
  - [ ] MECHANICAL: AGENTS.md line "No pytest suite exists yet" is corrected — `tests/` has 16 files / 159 passing tests, and CI already runs them via `uv run python -m unittest discover -s tests`. Re-sync `goc/templates/AGENTS_GOC.md` if the corrected text lives there. Plugin mirrors synced; `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# CI silently skips `goc validate` on the real deck after the deck move

## Handoff required (2026-05-27)

The autonomous drain bot implemented the fix below and verified it
(reproduce.py exit 0, `goc validate` clean, plugin-sync clean), but
**could not ship it**: the change touches `.github/workflows/ci.yml`,
and the bot's GitHub App token lacks the `workflows` permission
(`remote rejected … refusing to allow a GitHub App to create or update
workflow … without workflows permission`). This is the same structural
limit AGENTS.md documents ("the autonomous bot's `GITHUB_TOKEN` cannot
edit files under `.github/workflows/`").

The bot reverted its uncommitted ci.yml + AGENTS.md edits to keep the
shared `main` push path clean, and parked this card at `human_gate:
session`. **A maintainer with `workflows` push permission must apply
the ready-to-paste diff in the "## Fix" section below and the AGENTS.md
correction, then push.** No code investigation is needed — the fix is
fully specified.

## Location

- `.github/workflows/ci.yml` — final step "Validate deck (if exists)":
  ```yaml
  - name: Validate deck (if exists)
    run: |
      if [ -d deck ]; then
        goc validate
      else
        echo "No deck/ directory yet — skipping validation."
        echo "(once goc install scaffolds the repo, this step becomes load-bearing)"
      fi
  ```

## What's broken

The canonical deck moved from `deck/` to `.game-of-cards/deck/` in commit
`9fa3a24` ("deck: move canonical deck from deck/ to .game-of-cards/deck"). The
engine resolves `DECK_DIR` to `.game-of-cards/deck/` with only a *legacy*
`deck/` fallback, and root `deck/` no longer exists in the tree.

But the CI step still tests `if [ -d deck ]`. Since that directory is gone, CI
always takes the `else` branch and prints "No deck/ directory yet — skipping
validation." So `goc validate` — which AGENTS.md describes as the gate that
keeps card frontmatter consistent — **never runs on the real deck in CI**.

This contradicts the project's own stated guarantee. AGENTS.md (Common
commands):

> No pytest suite exists yet. `.github/workflows/ci.yml` is a build +
> console-script + `goc validate` smoke matrix on Python 3.10-3.13; the
> validation step is what gates card-frontmatter drift.

The validation step is precisely what is *not* running.

The local `pre-commit` hook `goc-validate` (in `.pre-commit-config.yaml`,
`files: ^(\.game-of-cards/deck/|goc/|claude-plugin/).*$`) still validates on
commit, so drift is caught locally. But CI does not run pre-commit, so a card
with broken frontmatter pushed by someone without the hook installed — or any
path that bypasses pre-commit — would pass CI green.

### Adjacent stale documentation in the same file

The `ci.yml` header comment is also stale:

> #   - All 11 skill templates ship as importable package data

There are 17 skill templates today (`ls goc/templates/skills/ | wc -l`), and the
comment's reference to "the repo's own `deck/` directory" / the
`goc-install-command-scaffolds-repo` card predates the `.game-of-cards/deck/`
move.

Separately, the AGENTS.md "No pytest suite exists yet" line is false: `tests/`
holds 16 files and 159 passing tests, and CI already runs them
(`Run regression tests` step: `uv run python -m unittest discover -s tests`).

## Empirical evidence

```
$ uv run python .game-of-cards/deck/ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory/reproduce.py
legacy root deck/ exists:          False
canonical .game-of-cards/deck/:    True (224 cards)
CI guard `[ -d deck ]` evaluates:  False  -> CI SKIPS `goc validate`
RESULT: DEFECT — CI never validates the real deck
```

## Why it matters

`goc validate` is the only mechanism that enforces card-frontmatter referential
integrity (relationship-edge invariants, enum validity, schema conformance)
across the whole deck. AGENTS.md explicitly designates it the CI gate. With the
guard pointed at a path that no longer exists, that gate has been silently dead
since the deck move — drift that a contributor introduces without the local
pre-commit hook installed sails through CI green. The fix is a one-line path
correction plus refreshing the surrounding stale comments.

## Fix

In `.github/workflows/ci.yml`, point the guard at the canonical path (keeping a
legacy fallback is optional since the engine still has one):

```yaml
- name: Validate deck
  run: |
    if [ -d .game-of-cards/deck ] || [ -d deck ]; then
      goc validate
    else
      echo "No deck directory yet — skipping validation."
    fi
```

Then refresh the stale `ci.yml` header comment (skill count, deck path) and
correct the AGENTS.md "No pytest suite exists yet" line (and its
`goc/templates/AGENTS_GOC.md` source if the text lives there) to reflect the
real `tests/` suite that CI already runs.

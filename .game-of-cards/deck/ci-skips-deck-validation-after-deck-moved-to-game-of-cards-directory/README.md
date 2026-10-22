---
title: ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory
summary: "CI's final step guarded on `if [ -d deck ]`, but the canonical deck moved to `.game-of-cards/deck/` (commit 9fa3a24). Root `deck/` no longer exists, so CI silently took the `No deck/ directory yet — skipping validation` branch and never ran `goc validate` on the real deck — the frontmatter-drift gate was dead in CI, which let a summary-less card keep `goc validate` red on main from 2026-08-13 to 2026-10-22. Fixed from a human session: the step now guards on `.game-of-cards/deck` (legacy `deck/` fallback kept) and the stale header comment is refreshed."
status: done
stage: null
contribution: high
created: "2026-05-27T00:53:41Z"
closed_at: "2026-10-22T05:09:05Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — the CI deck-validate step's path guard resolves to the canonical deck directory and would invoke `goc validate` on the real deck.
  - [x] MECHANICAL: `.github/workflows/ci.yml` "Validate deck" step guards on `.game-of-cards/deck` (with legacy `deck/` fallback if desired), so `goc validate` actually runs on this repo's own deck in CI.
  - [x] MECHANICAL: the stale `ci.yml` header comment is refreshed — it still says "All 11 skill templates" (there are 17) and refers to "the repo's own `deck/` directory" / the old scaffolding card; reword to match the `.game-of-cards/deck/` reality.
  - [x] ~~MECHANICAL: AGENTS.md line "No pytest suite exists yet" is corrected — `tests/` has 16 files / 159 passing tests, and CI already runs them via `uv run python -m unittest discover -s tests`. Re-sync `goc/templates/AGENTS_GOC.md` if the corrected text lives there. Plugin mirrors synced; `uv run goc validate` clean.~~ — **moot**: commit 99c58114 (2026-05-27, `agents-md-claims-no-test-suite-but-ci-runs-regression-tests`) already replaced the line with a description of the `tests/` regression suite; `uv run goc validate` is clean and the mirrors are in sync.
worker: {who: "claude[bot]", where: main}
---

# CI silently skips `goc validate` on the real deck after the deck move

> **Fixed 2026-10-22** from a human session. The autonomous drain bot
> had implemented and verified the fix on 2026-05-27 but could not ship
> it: the bot's GitHub App token lacks the `workflows` permission
> (`remote rejected … refusing to allow a GitHub App to create or update
> workflow … without workflows permission`), so the card waited at
> `human_gate: session` until a maintainer applied the "## Fix" below.
> The sections up to "## Fix" describe the defect as found.

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

Applied: `.github/workflows/ci.yml` now guards the step on the canonical
path, with the legacy fallback kept because the engine still has one:

```yaml
- name: Validate deck
  run: |
    if [ -d .game-of-cards/deck ] || [ -d deck ]; then
      goc validate
    else
      echo "No deck directory yet — skipping validation."
    fi
```

The header comment no longer counts skill templates ("All 11" had
drifted to 18) and names `.game-of-cards/deck/` and the regression
suite. The AGENTS.md "No pytest suite exists yet" line was already
corrected by 99c58114, so that DoD item is struck as moot.

Turning the step back on needed a green deck first: `goc validate`
had been red on main since 2026-08-13 because
`runtime-hooks-fire-in-repos-that-never-opted-in` carried no summary,
and nothing in CI noticed. That card got its summary in 494291ff,
right before this fix.

## Decision

*Resolved 2026-10-22T05:07:53Z:* Apply the documented ci.yml fix from a human session: guard the validate step on .game-of-cards/deck with the legacy deck/ fallback and refresh the stale header comment

*Reasoning:* The maintainer approved it in a human session on 2026-10-22; the fix was fully specified and only needed a human commit, since the bot token cannot push .github/workflows/


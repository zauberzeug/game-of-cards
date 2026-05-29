---
title: goc-new-next-hint-points-at-stale-deck-path-not-game-of-cards-deck
summary: "`goc new` prints a `Next: edit deck/<title>/README.md ...` hint that points at the legacy `deck/` directory, not the canonical `.game-of-cards/deck/` where the card was actually written one line earlier. Any agent that follows the hint hits ENOENT. Regression after the deck relocation."
status: done
stage: null
contribution: medium
created: "2026-05-29T13:26:01Z"
closed_at: "2026-05-29T13:30:26Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (the printed hint references the canonical card path)
  - [x] MECHANICAL: `goc/engine.py:4156` rewritten to use `card_dir.relative_to(REPO_ROOT)/` (mirroring the `created` line directly above)
  - [x] TDD: `uv run python -m unittest discover -s tests` green
  - [x] MECHANICAL: `pre-commit run --all-files` green (plugin mirrors stay in sync)
worker: {who: "claude[bot]", where: main}
---

# `goc new` "Next:" hint points at the stale `deck/` path

## Location

`goc/engine.py:4155-4156` — the two-line hint block at the end of the
`new` command.

## What's broken

Line 4155 prints the real card path (resolved via `DECK_DIR`,
canonical `.game-of-cards/deck/`). Line 4156 hardcodes the legacy
`deck/` prefix:

```python
print(f"created {card_dir.relative_to(REPO_ROOT)}/")
print(f"Next: edit deck/{title}/README.md to fill the body and DoD; then ask your agent to implement the card.")
```

This contradicts the closed card
[move-deck-into-game-of-cards-directory](../move-deck-into-game-of-cards-directory/),
which relocated every deck path to `.game-of-cards/deck/` and shipped
the `DECK_DIR` resolver precisely so future code references the
canonical location. The first print uses `DECK_DIR`; the second
silently doesn't.

## Empirical evidence

Reproduced on `main` while scaffolding this very card:

```
$ uv run goc new goc-new-next-hint-points-at-stale-deck-path-not-game-of-cards-deck --contribution medium --gate none --tag bug --tag api-contract
created .game-of-cards/deck/goc-new-next-hint-points-at-stale-deck-path-not-game-of-cards-deck/
Next: edit deck/goc-new-next-hint-points-at-stale-deck-path-not-game-of-cards-deck/README.md to fill the body and DoD; then ask your agent to implement the card.
```

Line 1: real path. Line 2: a path that does not exist on disk.

## Why it matters

The closed predecessor
[cli-output-suggests-next-step-after-each-verb](../cli-output-suggests-next-step-after-each-verb/)
established verb-stdout as the LLM's primary handoff channel — every
verb prints a one-line "Next:" hint sized for the agent's next tool
call. An LLM that reads `Next: edit deck/<title>/README.md` will
naturally emit `Read(.../deck/<title>/README.md)` or
`Edit(.../deck/<title>/README.md)` as its next action — and ENOENT
against a non-existent path. The card filed via the in-skill
`Skill(create-card)` flow lives at `.game-of-cards/deck/<title>/`, so
the agent has to discover and correct the path on its own every time
`goc new` runs.

Reachability path: every `goc new <title>` invocation prints this
hint. `Skill(create-card)` is the canonical filing flow, so every
audit-deck round, every user-initiated "I want to track X", every
`/loop` that produces a follow-up card hits this. The defect is on
the agent-handoff substrate, not in a rarely-walked code path.

This is a regression on the `cli-output-suggests-next-step-after-each-verb`
contract introduced by the
[move-deck-into-game-of-cards-directory](../move-deck-into-game-of-cards-directory/)
migration — the path resolver was updated everywhere except in the
human-facing hint string.

## Fix

Replace line 4156 with the same path expression line 4155 uses:

```python
print(f"created {card_dir.relative_to(REPO_ROOT)}/")
print(f"Next: edit {card_dir.relative_to(REPO_ROOT)}/README.md to fill the body and DoD; then ask your agent to implement the card.")
```

One-line mechanical fix. No other `goc` verb prints a path hint that
hardcodes `deck/` (greps clean — `_cmd_status`, `_cmd_done`, `_cmd_wait`,
`_cmd_advance`, `_cmd_decide` either print no path or print
`relative_to(REPO_ROOT)`-derived paths). The migration of slugs inside
URLs at `engine.py:4427` (`text.replace(f"deck/{old}/", f"deck/{new}/")`)
is unrelated — that rewrites content references inside card bodies,
which is a separate documented convention.

After the engine edit, re-run pre-commit so the plugin mirrors at
`claude-plugin/goc/engine.py`, `codex-plugin/goc/engine.py`, and
`openclaw-plugin/goc/engine.py` resync from the source-of-truth.

---
title: deck-readme-hook-catalogue-omits-refine-deck-hook
status: done
stage: null
contribution: low
created: "2026-06-19T05:05:40Z"
closed_at: "2026-06-19T05:09:11Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [x] TDD: a regression test asserts every shipped `goc/templates/game_of_cards/hooks/*.md` stub has a matching row in the README "Workflow-hook stubs" table (fails before the fix, passes after).
  - [x] MECHANICAL: the `refine-deck` row is added to the "Workflow-hook stubs" table in `goc/templates/game_of_cards/README.md` and the dogfood copy `.game-of-cards/README.md`.
  - [x] MECHANICAL: `uv run goc validate` is clean and the full regression suite passes.
worker: {who: "claude[bot]", where: main}
---

# README hook-point catalogue omits the shipped `refine-deck` hook

## Summary
The deck README's "Workflow-hook stubs" table lists only five hooks, but a
sixth hook stub (`hooks/refine-deck.md`) ships and is actively injected into
the `refine-deck` skill body. A consumer reading the catalogue to discover
extension points cannot find the `refine-deck` hook-point.

## Location
- Doc (stale catalogue): `goc/templates/game_of_cards/README.md` —
  "Workflow-hook stubs (`hooks/<skill>.md`)" table.
- Dogfood copy with the same omission: `.game-of-cards/README.md`.

## What's broken
The README table enumerates the workflow-hook stubs:

```
| Hook | Loaded by | Workflow point |
|---|---|---|
| `hooks/create-card.md` | `create-card` | ... |
| `hooks/decide-card.md` | `decide-card` | ... |
| `hooks/finish-card.md` | `finish-card` | ... |
| `hooks/pull-card.md` | `pull-card` | ... |
| `hooks/audit-deck.md` | `audit-deck` | ... |
```

But a sixth stub ships beside those five:

```
$ ls goc/templates/game_of_cards/hooks/
audit-deck.md  create-card.md  decide-card.md
finish-card.md  pull-card.md  refine-deck.md
```

and the `refine-deck` skill actively `!cat`-injects it
(`goc/templates/skills/refine-deck/SKILL.md:12`):

```
!`cat .game-of-cards/hooks/refine-deck.md 2>/dev/null || true`
```

The stub's own header tells authors "See the goc README for the hook-point
catalogue" — but that catalogue is missing the `refine-deck` row, so the
pointer is circular and dead-ends.

## Why it matters
Every consumer who runs `goc install` / `goc upgrade` receives this README
verbatim. The catalogue is the documented index of extension points; an
author looking to customize the `refine-deck` hygiene pass scans the table,
does not see `refine-deck`, and concludes (wrongly) that no such hook-point
exists. The drift was introduced by the closed card
[refine-deck-skill-missing-consuming-repo-hook-override](../refine-deck-skill-missing-consuming-repo-hook-override/),
which added the injection and the stub but never updated the catalogue.

## Fix
Add a `refine-deck` row to the "Workflow-hook stubs" table in both
`goc/templates/game_of_cards/README.md` (source of truth, shipped to
consumers) and the dogfood `.game-of-cards/README.md`. Add a regression
test asserting the table stays in sync with the shipped `hooks/*.md` set so
the next added hook can't silently drift again.

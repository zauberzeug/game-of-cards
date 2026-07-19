---
title: legacy-config-fallback-points-at-a-filename-goc-never-wrote
summary: "`LEGACY_DECK_CONFIG_FILE` reads `.claude/config.yaml`, but the pre-move config home was `.claude/deck-config.yaml` — the name the upgrade migration uses and the name the introducing commit promised to keep reading. The fallback has never matched a real legacy config: authored closure checks and the `auto_commit: false` opt-out are silently ignored until an upgrade migrates the file. Bonus hazard: an unrelated tool's `.claude/config.yaml` would be parsed as GoC deck config."
status: open
stage: null
contribution: medium
created: "2026-07-19T04:08:07Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` (correct the filename vs drop the fallback).
  - [ ] TDD: `uv run python .game-of-cards/deck/legacy-config-fallback-points-at-a-filename-goc-never-wrote/reproduce.py` exits zero (legacy `.claude/deck-config.yaml` is read, or the fallback is removed and the repro updated to assert that contract).
  - [ ] TDD: regression test covers `load_deck_config()` behavior for a repo whose only config is the legacy file.
  - [ ] MECHANICAL: `get_skills_source`'s docstring ("or the legacy `.claude/config.yaml`") and any other mention of the legacy path match the decided behavior.
---

# The engine's legacy-config fallback reads `.claude/config.yaml`, a filename GoC never wrote

## Location

- `goc/engine.py:150` — `LEGACY_DECK_CONFIG_FILE = DECK_ROOT / ".claude" / "config.yaml"`
- `goc/engine.py:4720` — consumption: `for path in (GAME_OF_CARDS_CONFIG_FILE, LEGACY_DECK_CONFIG_FILE):`
- `goc/install.py:1071` — the upgrade migration's contrasting (correct)
  name: `legacy_config = target / ".claude" / "deck-config.yaml"`
- `goc/templates/game_of_cards/README.md:24` — "Legacy
  `.claude/deck-config.yaml` is migrated here on upgrade."

## What's broken

The pre-move config home was `.claude/deck-config.yaml` (removed
constant `DECK_CONFIG_FILE`, commit `fe651865`, whose message promises
the engine keeps "still reading legacy .claude/deck-config.yaml"). But
the fallback constant that same commit introduced points at
`.claude/config.yaml` — a filename no GoC version ever wrote. Two
source locations disagree about what "legacy config" means: the
engine's fallback (`goc/engine.py:150`) and the upgrade migration
(`goc/install.py:1071`). The migration is right; the fallback has been
dead code since the day it landed.

Consequences for a legacy repo that hasn't run `goc upgrade`:
`load_deck_config()` returns the empty default, so authored
`layer_2_project_dod` / `layer_3_goc_dod` closure checks vanish from
`goc attest`, and `workflow.auto_commit: false` is ignored — mutating
verbs auto-commit against an explicit opt-out. Secondary hazard: the
constant as written parses any unrelated tool's `.claude/config.yaml`
as GoC deck config.

## Empirical evidence

`uv run python .game-of-cards/deck/legacy-config-fallback-points-at-a-filename-goc-never-wrote/reproduce.py`:

```
load_deck_config() with real legacy .claude/deck-config.yaml:
  {'layer_2_project_dod': [], 'layer_3_goc_dod': []}
load_deck_config() with the engine's expected .claude/config.yaml:
  {'workflow': {'auto_commit': False}, 'layer_2_project_dod': [{'name': 'project-test-suite', 'cmd': 'true'}]}
FAIL: authored legacy config silently ignored — layer-2 closure checks and the auto_commit opt-out vanish (the engine fallback reads a filename goc never wrote)
[exit 1]
```

The control run (same content at the filename the engine expects)
loads cleanly — the loader works; only the filename is wrong.

## Why it matters

Reachability: any repo installed before the config move (commit
`fe651865`) that has not yet run `goc upgrade` carries its config at
`.claude/deck-config.yaml`. On every engine invocation in such a repo,
the documented fallback contract — and the closed card
[move-deck-config-to-game-of-cards-config](../move-deck-config-to-game-of-cards-config/)'s
"clear migration path" promise — silently fails open: closure
attestation runs with zero configured checks and auto-commit ignores
the opt-out. The failure is invisible (no warning, valid defaults).

## Decision required

1. **Correct the constant** to `.claude/deck-config.yaml` — restores
   the promised fallback for un-upgraded legacy repos; one-line fix.
2. **Drop the fallback entirely** — the fallback has never worked, so
   no repo can depend on it; `goc upgrade` migration becomes the only
   legacy path. Also removes the foreign-file-swallowing hazard and
   simplifies `load_deck_config()` / `get_skills_source()`.
3. **Read both names** in the fallback tuple — maximally forgiving,
   keeps the hazard.

Option 2 is cleanest if un-upgraded legacy repos are considered out of
support; option 1 if the fe651865 contract should be honored.

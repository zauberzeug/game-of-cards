---
title: unrelated-deck-folder-trips-dual-tree-refusal-and-migrate-deletes-it
summary: "`_resolve_deck_dir` flags a dual-tree conflict on a bare `exists()` check — any unrelated top-level `deck/` folder (slide deck, card-game assets) hard-blocks every verb. The error's suggested remediation, `goc migrate`, then ingests the folder's subdirectories as cards and `shutil.rmtree`s the folder, silently destroying its top-level files. The engine and `install._find_installed_deck_dir` (which requires `deck/.goc-version`) disagree on what counts as a deck."
status: open
stage: null
contribution: high
created: "2026-06-12T05:40:59Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: deck-identity predicate chosen (Decision required below) and recorded in log.md.
  - [ ] TDD: reproduce.py exits zero inverted — with an unrelated `deck/` folder present, goc verbs operate on the canonical tree and `goc migrate` refuses to ingest or delete the non-deck folder.
  - [ ] TDD: regression test covers (a) unrelated `deck/` + canonical tree, (b) real legacy card deck + canonical tree (refusal must still fire), (c) legacy-only unrelated `deck/` (must NOT silently become the deck).
  - [ ] TDD: `goc migrate` never deletes top-level files in `deck/` that were not copied (existing data-loss shape shared with goc-migrate-silently-destroys-card-files-other-than-readme-and-log).
  - [ ] MECHANICAL: plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green).
---

# Unrelated `deck/` folder trips the dual-tree refusal — and `goc migrate` deletes it

`_resolve_deck_dir` decides "this repo has a legacy card deck" from a bare
`Path.exists()` check on `<repo>/deck/`. A repo whose `deck/` is a slide
deck, a card-game asset folder, or a ship-deck model gets every goc verb
hard-blocked with the dual-tree refusal; following the error's own
remediation (`goc migrate`) ingests the folder's subdirectories into
`.game-of-cards/deck/` as "cards" and then deletes the folder wholesale —
top-level files are destroyed without ever being copied.

## Location

- `goc/engine.py:107` — `if canonical.exists() and legacy.exists(): _DUAL_TREE_CONFLICT = True`
- `goc/engine.py:3115` — every verb except `migrate` exits 1 on the conflict, suggesting `goc migrate`
- `goc/engine.py:5217` — `legacy_dirs = {d.name: d for d in legacy.iterdir() if d.is_dir()}` (only dirs are ever copied)
- `goc/engine.py:5287` — `shutil.rmtree(legacy)` (deletes the whole folder, including never-copied top-level files)
- `goc/install.py:453-461` — `_find_installed_deck_dir` requires `deck/.goc-version` before treating `deck/` as a GoC install (the contrasting predicate)

## What's broken

The engine's deck-identity predicate:

```python
canonical = repo_root / ".game-of-cards" / "deck"
legacy = repo_root / "deck"
if canonical.exists() and legacy.exists():
    _DUAL_TREE_CONFLICT = True
```

No card-shape check, no sentinel. The installer disagrees:
`_find_installed_deck_dir` only recognizes a legacy `deck/` when
`deck/.goc-version` exists — a derivation gap between two modules that are
supposed to share one concept. The migrate verb compounds it: subdirs of
the unrelated folder are classified as legacy-only "cards" and copied into
the canonical deck (where they immediately fail validation), and
`shutil.rmtree(legacy)` removes the user's folder — top-level *files* in
it are deleted without ever being copied, because the migration loop only
walks directories. With the canonical tree absent, the unrelated folder
silently *becomes* the deck (`_LEGACY_ONLY` path).

## Empirical evidence

`uv run python .game-of-cards/deck/unrelated-deck-folder-trips-dual-tree-refusal-and-migrate-deletes-it/reproduce.py`:

```
[goc (list)] exit=1
  stderr: ERROR: two deck trees found — cannot operate safely:
[goc migrate --yes] exit=0
  Cards to migrate (legacy-only):
    deck/slides/  →  .game-of-cards/deck/slides/
    migrated: slides

  Removed legacy tree: /tmp/goc-deck-collision-x67io93d/repo/deck
  Migration complete. Run `goc validate` to confirm.

legacy deck/ removed:              True
notes.txt content survives anywhere: False
slides/ ingested as a 'card':        True

DEFECT CONFIRMED: an unrelated deck/ folder hard-blocks every verb, and the suggested `goc migrate` destroys its top-level files and ingests its subdirectories as cards.
```

## Why it matters

Reachability: consuming repos with a pre-existing `deck/` directory are
common — presentation decks, card-game assets, ship decks. Any such repo
that installs GoC gets every verb blocked the moment both paths exist, and
the tool's own printed remediation is a data-destruction command. The
closed card
[engine-refuses-to-start-when-both-deck-trees-exist](../engine-refuses-to-start-when-both-deck-trees-exist/)
designed the refusal for *real* legacy card decks after a dual-tree drift
incident; the false-positive misidentification and migrate-side
destruction of non-deck content were never in scope there. The in-card
file-loss sibling is
[goc-migrate-silently-destroys-card-files-other-than-readme-and-log](../goc-migrate-silently-destroys-card-files-other-than-readme-and-log/)
— same `rmtree`, different victim class; a fix here should coordinate with
that card.

## Decision required

What predicate makes a top-level `deck/` directory a *card deck*?

1. **Sentinel-gated (match the installer)** — only treat `deck/` as
   legacy when `deck/.goc-version` exists, mirroring
   `_find_installed_deck_dir`. Pre-sentinel legacy decks (created before
   the sentinel existed) would stop being detected — is that population
   empty by now?
2. **Card-shape probe** — treat `deck/` as legacy when at least one
   subdirectory contains a `README.md` with parseable GoC frontmatter
   (`title:` + `status:`). Catches pre-sentinel decks, costs a read, has
   a (small) false-positive surface.
3. **Sentinel OR card-shape** — union of 1 and 2: sentinel wins fast,
   shape-probe rescues pre-sentinel decks. Slightly more code, covers
   both populations.

Orthogonally, `goc migrate` should refuse (or skip with a warning) any
"card" lacking GoC frontmatter, and must never `rmtree` a tree containing
files it did not copy — that half overlaps the open migrate data-loss
card and should be decided together.

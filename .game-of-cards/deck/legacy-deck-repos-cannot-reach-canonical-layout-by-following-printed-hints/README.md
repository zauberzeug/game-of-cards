---
title: legacy-deck-repos-cannot-reach-canonical-layout-by-following-printed-hints
summary: "On a legacy-only repo (deck/ with .goc-version, no .game-of-cards/deck/), the three verbs the tool points at form a closed loop: the engine warns 'Run goc upgrade to migrate', but upgrade never creates .game-of-cards/deck/ (it only migrates the legacy config file and re-stamps the legacy sentinel); goc migrate refuses with 'Run goc install first'; goc install refuses with 'Run goc upgrade'. No printed hint reaches the canonical layout — the only escape is an undocumented manual mkdir."
status: open
stage: null
contribution: medium
created: "2026-07-24T01:09:58Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, documentation, unverified]
definition_of_done: |
  - [ ] TDD: a committed `reproduce.py` scaffolds a legacy-only repo in a temp dir and demonstrates the closed loop (migrate exits 1 pointing at install; install exits 1 pointing at upgrade; upgrade exits 0 yet `.game-of-cards/deck/` still absent; migrate exits 1 again) — drop the `unverified` tag when it lands.
  - [ ] MECHANICAL: the chosen fix (see `## Decision required`) lands so that at least one printed hint, followed literally, reaches the canonical layout.
  - [ ] TDD: a regression test covers the legacy-only escape path end-to-end and the suite passes.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# Legacy deck repos cannot reach the canonical layout by following printed hints

## Summary

A repo with only the legacy layout (`deck/` containing `.goc-version`, no
`.game-of-cards/deck/`) is told by every verb to run a different verb, and
none of them performs the migration. The three hints form a closed loop with
no documented exit.

## Location

- `goc/engine.py:3687-3691` — every non-exempt verb warns:

  ```python
  if _LEGACY_ONLY and args.command not in ("migrate", "install", "upgrade", None):
      print(
          "WARNING: using legacy deck/ location. Run `goc upgrade` to migrate to .game-of-cards/deck/.",
          ...
  ```

- `goc/install.py:1665-1833` — `upgrade()` never migrates the deck tree:
  `_find_installed_deck_dir` (`goc/install.py:455-463`) resolves the legacy
  `deck/`, the sentinel is re-stamped *there*
  (`goc/install.py:1825`), and `_sync_game_of_cards_config(...,
  migrate_legacy=True)` (`goc/install.py:1074-1075`) migrates only the
  legacy `.claude/deck-config.yaml` config file — it never creates
  `.game-of-cards/deck/`.
- `goc/engine.py:6246-6252` — `goc migrate` refuses legacy-only repos:
  `"ERROR: canonical deck location {canonical} does not exist.\n Run \`goc
  install\` first to set up the canonical deck location."`
- `goc/install.py:1540-1546` — `goc install` refuses in turn (its
  `_find_installed_deck_dir` also matches legacy `deck/.goc-version`):
  `"already installed ({rel}/.goc-version → {existing})"` / `"Run \`goc
  upgrade\` to re-sync templates."`

## What's broken

The engine's warning promises "`goc upgrade` to migrate to
`.game-of-cards/deck/`" — a claim the upgrade code never fulfills. Following
the hints literally: `migrate` → "run install" → `install` → "run upgrade" →
`upgrade` → exit 0, "upgrade complete", legacy `deck/` untouched, canonical
dir still absent → `migrate` fails identically. The only escape is a manual
`mkdir -p .game-of-cards/deck` (documented nowhere), which then routes
through the dual-tree state.

## Evidence (unverified — no committed reproduce.py yet)

A hunter agent reproduced the full loop in a scratch git repo containing only
`deck/my-card/` + `deck/.goc-version`:

- `goc migrate` → exit 1, "Run `goc install` first"
- `goc install` → exit 1, "Run `goc upgrade` to re-sync templates"
- `goc upgrade` → exit 0, "upgrade complete — 0.0.20 → 0.0.27", yet
  `.game-of-cards/deck` still absent and `deck/.goc-version` re-stamped in
  place
- `goc migrate` again → exit 1, unchanged

Falsification recipe: scaffold that repo shape in a temp dir and run the
four commands above; the defect is disproved if any of them creates
`.game-of-cards/deck/` or prints a hint that, followed literally, does.

## Why it matters

Legacy-layout consumers exist by construction — the engine ships a dedicated
`_LEGACY_ONLY` code path, a deprecation warning, and a `migrate` verb
specifically for them. Every one of those repos sees a migration instruction
that does not work, and `upgrade`'s success message ("upgrade complete")
actively hides that the promised migration never happened. Reachability
path: any pre-`.game-of-cards` install → engine `_LEGACY_ONLY` warning →
the verb circle above.

## Decision required

1. **Make `goc upgrade` honor its own hint.** On a legacy-only repo,
   upgrade performs (or offers) the deck-tree migration before re-stamping
   the sentinel — matching the warning text verbatim.
2. **Make `goc migrate` accept legacy-only repos.** Drop the
   canonical-dir precondition: create `.game-of-cards/deck/` and move the
   legacy tree in one verb; leave upgrade alone and reword the engine
   warning to point at `goc migrate`.
3. **Documentation-only.** Keep behavior, fix the three printed hints to
   spell out the real escape (`mkdir -p .game-of-cards/deck` then `goc
   migrate`, or whatever sequence the maintainer blesses).

Options 1 and 2 change verb semantics with destructive-move implications
(compare [goc-migrate-silently-destroys-card-files-other-than-readme-and-log](../goc-migrate-silently-destroys-card-files-other-than-readme-and-log/)
and [unrelated-deck-folder-trips-dual-tree-refusal-and-migrate-deletes-it](../unrelated-deck-folder-trips-dual-tree-refusal-and-migrate-deletes-it/)
before choosing); option 3 is safe but leaves a two-command manual ritual.

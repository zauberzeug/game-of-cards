---
title: skill-references-cite-nonexistent-goc-next-verb
status: done
stage: null
contribution: low
created: "2026-07-22T13:18:58Z"
closed_at: "2026-07-22T13:25:55Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
summary: "Two source-of-truth skill reference files describe the draft-hiding contract as applying to \"`goc`, `goc next`\" — but no `next` subcommand exists (`goc next` exits 2 with `invalid choice`). The drift ships to all six consumer surfaces via the mirrors. Fix: cite the real surfaces (`goc`, `goc --ready`, `card_is_ready`) and re-sync/re-port."
definition_of_done: |
  - [x] MECHANICAL: `goc/templates/skills/card-schema/reference.md` and `goc/templates/skills/create-card/reference.md` no longer mention `goc next`; the draft-hiding sentence cites surfaces that exist (`goc`, `goc --ready`, `card_is_ready`).
  - [x] MECHANICAL: mirrors regenerated — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` both clean; no `goc next` remains under any template or mirror tree (grep, deck card bodies exempt as historical records).
  - [x] PROCESS: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# Skill references cite a nonexistent `goc next` verb

## Location

- `goc/templates/skills/card-schema/reference.md:68`
- `goc/templates/skills/create-card/reference.md:96`

## What's broken

Both reference files document the draft-hiding contract against a CLI
verb that does not exist:

```
- Hidden from the default queue (`goc`, `goc next`, `card_is_ready`)
```

```
queue (`goc`, `goc next`) and protected from dedup/supersede
```

But the engine's subcommand set has never included `next`:

```
$ goc next
goc: error: argument command: invalid choice: 'next' (choose from 'validate', 'quality-pass', 'done', ...)   # exit 2
```

"Next" is a *skill* (`Skill(next-card)`), not a CLI verb. The actual
draft-hiding surfaces (engine.py `filter_cards` + `card_is_ready`) are
the default queue and every filtered listing except `--status all`,
plus the `card_is_ready` predicate used by next-card/pull-card — so
the accurate citation is `goc`, `goc --ready`, `card_is_ready`.

Because these are source-of-truth templates, the phantom verb ships to
all six consumer surfaces (claude-plugin, codex-plugin,
openclaw-plugin, `.claude/skills`, `.codex/skills`, `goc install`
targets) — an agent reading the skill cold may try to run `goc next`
and burn a correction round on the exit-2 error.

## Why it matters

Skill bodies are the methodology contract agents follow verbatim in
consuming repos; a cited command that exits 2 is doc drift of the
exact kind `goc validate`-era cards exist to retire. Nearest existing
cards ([next-card-reclassify-checklist-cites-nonexistent-docs-framework-path](../next-card-reclassify-checklist-cites-nonexistent-docs-framework-path/),
closed `next-card-impact-ladder-references-nonexistent-frontmatter-field`)
concern the next-card skill's own content, not a phantom CLI verb
cited from card-schema/create-card references.

## Fix (applied)

Replaced `goc next` with `goc --ready` in the two template lines,
regenerated the mirrors via `scripts/sync_plugin_assets.py` (8 files)
and re-ran `scripts/port_skills_to_openclaw.py`; both `--check` modes
are clean and `grep -rn "goc next"` finds no hit outside historical
deck card bodies. Regression suite: 752 tests, OK.

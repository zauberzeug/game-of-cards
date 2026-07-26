---
title: hook-mirrors-and-openclaw-dist-lack-linguist-generated-marker
summary: ".gitattributes marked the seven skill/engine mirror trees linguist-generated but not the equally auto-synced hook mirrors (claude-plugin/hooks/, codex-plugin/hooks/, .claude/hooks/) or the committed esbuild bundle at openclaw-plugin/dist/, so one hook-template edit still rendered 4x in PR review — while the authored .claude/skills/tune-cadence/ dev skill was wrongly collapsed by the blanket skills rule. Fixed by adding the four generated trees plus explicit =false carve-outs for authored files, with tests/test_gitattributes_generated_markers.py deriving the synced-tree list from SYNC_PAIRS so future sync destinations cannot land unmarked."
status: done
stage: null
contribution: low
created: "2026-07-23T01:35:22Z"
closed_at: "2026-07-23T01:46:33Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra, documentation]
definition_of_done: |
  - [x] MECHANICAL: `.gitattributes` marks the three hook mirrors (`claude-plugin/hooks/**`, `codex-plugin/hooks/**`, `.claude/hooks/**`) and the committed esbuild bundle (`openclaw-plugin/dist/**`) `linguist-generated=true`, with explicit `=false` carve-outs for the authored files inside synced dirs (the two `hooks.json` twins and the repo-local `.claude/skills/tune-cadence/`).
  - [x] TDD: `reproduce.py` prints `DEFECT ABSENT` (12 generated files unmarked + 1 authored file collapsed before the fix; 0/0 after), and a unittest under `tests/` (`tests/test_gitattributes_generated_markers.py`) derives the synced-tree list from `scripts/sync_plugin_assets.py`'s SYNC_PAIRS and fails if a future sync destination lands without a `.gitattributes` rule or an authored file gets collapsed.
  - [x] MECHANICAL: `AGENTS.md`'s mirror-tree list (the "marked `linguist-generated=true`" paragraph) is extended to match the new rule set.
  - [x] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green (754 tests).
worker: {who: "claude[bot]", where: main}
---

# Hook mirrors and the OpenClaw dist bundle lack the linguist-generated marker

## Summary

`.gitattributes` marks the seven skill/engine mirror trees
`linguist-generated=true` so reviewers "see the authored change once
instead of N times across the mirrors" — but the equally auto-synced hook
mirrors (`claude-plugin/hooks/`, `codex-plugin/hooks/`, `.claude/hooks/`)
and the committed esbuild output at `openclaw-plugin/dist/` are unmarked,
so one hook-template edit still renders 4× in PR review. Conversely the
authored repo-local `tune-cadence` skill is swallowed by the existing
`.claude/skills/**` rule and its real authored diffs get collapsed.

## Location

- `.gitattributes:7-13` — seven patterns only (`*-plugin/goc/**`,
  `*-plugin/skills/**`, `.claude/skills/**`, `.codex/skills/**`); the
  header comment at `:1-6` states the once-not-N-times intent.
- `scripts/sync_plugin_assets.py:114-147, 196-203` — the three hook dirs
  are directory syncs of `goc/templates/hooks/` via the same `SYNC_PAIRS`
  mechanism as the marked mirrors (`hooks.json` is the only authored file,
  protected via `preserve_files`).
- `openclaw-plugin/package.json:37` — `dist/` is `esbuild` output
  (`npm run build`), committed and shipped; three tracked files.
- Doc twin: `AGENTS.md` § "The mirror trees … are marked
  `linguist-generated=true`" reproduces the same incomplete list.

## What's broken

The `.gitattributes` header states the contract:

> The diff content is duplication of changes already visible in `goc/` or
> `goc/templates/skills/`; marking these paths `linguist-generated` tells
> GitHub's review surface to collapse them by default, so reviewers see
> the authored change once instead of N times across the mirrors.

The hook mirrors are byte-copies of `goc/templates/hooks/*.py` produced by
the exact same sync (`sync_plugin_assets.py` dir-sync pairs), yet
`git check-attr linguist-generated -- claude-plugin/hooks/deck_prompt_router.py`
prints `unspecified` while the sibling `claude-plugin/skills/deck/SKILL.md`
prints `true`. The originating card
[trim-token-cost-of-autonomous-card-cycles](../trim-token-cost-of-autonomous-card-cycles/)
hard-coded the seven-pattern list in its DoD, so the hook mirrors and
`dist/` were never covered and nothing guards the list against new synced
trees.

## Empirical evidence

`uv run python .game-of-cards/deck/hook-mirrors-and-openclaw-dist-lack-linguist-generated-marker/reproduce.py`
(before the fix):

```
MISS .claude/hooks: 0/3 marked generated
OK   .claude/skills: 28/28 marked generated
OK   .codex/skills: 27/27 marked generated
OK   claude-plugin/goc: 30/30 marked generated
MISS claude-plugin/hooks: 1/4 marked generated
OK   claude-plugin/skills: 26/26 marked generated
OK   codex-plugin/goc: 30/30 marked generated
MISS codex-plugin/hooks: 1/4 marked generated
OK   codex-plugin/skills: 27/27 marked generated
MISS openclaw-plugin/dist: 0/3 marked generated
OK   openclaw-plugin/goc: 27/27 marked generated
  [12 unmarked generated files, 1 authored file collapsed]
DEFECT PRESENT: 12 generated file(s) unmarked, 1 authored file(s) wrongly collapsed
```

## Why it matters

Every hook-template edit (there are three shipped hooks, each with four
copies counting the template) shows its full diff four times in PR review,
and the `[sync auto]` commit-subject convention loses its GitHub-side
counterpart for exactly the hook half of the sync. The committed
`openclaw-plugin/dist/` bundle (~bundled JS + sourcemap) renders as
reviewable source on every `npm run build` commit. Meanwhile the authored
`tune-cadence` dev skill is collapsed by default, hiding real changes —
the inverse failure of the same list rot.

## Fix (applied)

`.gitattributes` now marks the three hook mirrors and
`openclaw-plugin/dist/**` `linguist-generated=true`, with `=false`
carve-outs placed after the globs (last matching line wins) for the two
`hooks.json` twins and `.claude/skills/tune-cadence/**`. The AGENTS.md
mirror-tree sentence lists the full set including the carve-outs, and
`tests/test_gitattributes_generated_markers.py` derives the expected-marked
set from `SYNC_PAIRS` (plus the codex skill trees and `dist/`) so the next
synced tree cannot land unmarked and no authored file can be collapsed.

After the fix, `reproduce.py` prints `OK` for all 11 trees and
`DEFECT ABSENT: every auto-synced tree is marked, every authored file
exempted`.

`openclaw-plugin/skills/` stays deliberately unmarked: the porter's output
is reviewed and committed by hand (AGENTS.md — "the porter applies
non-trivial normalization worth eyeballing"), so collapsing it would hide
exactly the review the process requires.

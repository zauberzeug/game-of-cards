---
title: goc-new-writes-duplicate-tags-when-tag-flag-is-repeated
summary: "`goc new` deduplicated `--advances` / `--advanced-by` through `_unique_preserving_order` but wrote `--tag` verbatim, so `--tag bug --tag bug` (or the global `goc --tag bug --tag bug new`) landed `tags: [bug, bug]` and `goc validate` stayed green. `_cmd_new` now dedupes `--tag` beside the edge flags, and a test tripwire holds every repeatable `goc new` flag to the same dedupe. No validate rule for already-filed duplicates: the deck holds none, and after the fix only a hand edit can add one."
status: done
stage: null
contribution: medium
created: "2026-05-30T06:30:27Z"
closed_at: "2026-10-30T04:27:38Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (defect no longer fires — `goc new --tag X --tag X` produces `tags: [X]`, not `[X, X]`) — exits 0 printing `tags written to disk: [bug, documentation]`; against the pre-fix engine it exits 1 with `[bug, bug, documentation, bug]`. The script was filed inverted (exit 0 while the defect fired) and was flipped to this contract.
  - [x] MECHANICAL: `_cmd_new` deduplicates `tags` the same way it deduplicates `advances` / `advanced_by` (via `_unique_preserving_order`) — `tags = _unique_preserving_order(args.tags or [])`, moved beside the two edge lines; it covers the global `--tag` path too.
  - [x] PROCESS: decide whether `goc validate` should also flag pre-existing duplicates in already-filed cards (separate sibling card if yes) — decided no, so no sibling card: `_cmd_new` is the only writer of `tags`, no card in the deck repeats a list entry (823 scanned on 2026-10-30), and the engine already treats repeated list entries as a reader concern. Reasoning in the body.
  - [x] TDD: a regression test in `tests/` covers `goc new --tag bug --tag bug` — `tests/test_new_dedupes_repeated_list_flags.py`, 4 tests, 3 of which fail against the pre-fix engine; its tripwire fails the build when `goc new` gains a repeatable flag its table does not list.
  - [x] PROCESS: `uv run goc validate` passes — exit 0; the full suite is green too (1432 tests).
worker: {who: "claude[bot]", where: main}
---

# `goc new` keeps duplicate `--tag` values

## Status

Fixed 2026-10-30. `_cmd_new` passes `--tag` through
`_unique_preserving_order` beside `--advances` / `--advanced-by`, so a
repeated value lands once, in first-seen order: `--tag bug --tag bug
--tag documentation --tag bug` writes `tags: [bug, documentation]`.
`goc validate` gains no duplicate-entry rule (see the last section).

## Location

`_cmd_new` in `goc/engine.py`: the three `_unique_preserving_order`
lines that read the repeatable flags (`args.tags`, `args.advances_wire`,
`args.advanced_by_wire`), and the `"tags": list(tags)` key of the
frontmatter it writes. `_cmd_new` is the only engine path that writes
`tags`; every other verb re-emits the parsed list unchanged.

## What was broken

`_cmd_new` read each repeatable (`action="append"`) flag from argparse
and deduplicated `advances` and `advanced_by` before touching disk:

```python
advances = _unique_preserving_order(args.advances_wire or [])
advanced_by = _unique_preserving_order(args.advanced_by_wire or [])
```

`--tag`, the third repeatable flag, was read as `tags = args.tags`,
checked value by value against the canonical-tag set, and written
through unchanged as `"tags": list(tags)`. The global `--tag` reaches
the same variable — `new --tag` defaults to `argparse.SUPPRESS`, so the
parent's list flows through when the subcommand flag is absent — and
`goc --tag bug --tag bug new <title>` duplicated too. `goc validate`
checks tag membership, not repetition, so the card stayed green.

## Empirical evidence

`reproduce.py` runs `goc install` and `goc new test-dedup-card --tag bug
--tag bug --tag documentation --tag bug` in a fresh temp repo (this
repo's deck is untouched) and prints the `tags:` line it wrote. Exit 0
means the defect no longer fires, exit 1 that it fires.

Against the pre-fix engine (exit 1):

```
tags written to disk: [bug, bug, documentation, bug]
DUPLICATES PRESENT — defect fires.
```

After the fix (exit 0):

```
tags written to disk: [bug, documentation]
No duplicates — defect no longer fires.
```

## Why it matters

Tags are a controlled vocabulary (`schema.canonical_tags` +
`.game-of-cards/canonical-tags.md`) whose `goc validate` check enforces
membership only, so `tags: [bug, bug]` was accepted silently. The
engine's own `goc --tag` filter is a membership test and does not
double-count, but the duplicate shows in the table's TAGS cell (which
spends one of its four slots on it) and in `goc --json`, where anything
counting tags per card — `Skill(retrospective)` clustering, a script
over the dump — counts the typo instead of the classification. Ordinary
one-shot authoring reached it: any `goc new <title> --tag X --tag X`.

Two of the three repeatable flags were deduplicated and the third was
not, a gap that reopens whenever `goc new` gains another repeatable
flag.

## Fix

- `goc/engine.py` `_cmd_new`: `tags = _unique_preserving_order(args.tags
  or [])`, moved beside the `advances` / `advanced_by` lines so the
  three repeatable flags are read in one place.
- `tests/test_new_dedupes_repeated_list_flags.py`: the subcommand and
  the global `--tag` path each write a repeated tag once, in first-seen
  order; one `goc new` with every repeatable flag doubled writes each
  value once and validates clean; and a tripwire enumerates the
  `action="append"` options on the `new` subparser, so a repeatable flag
  added later fails the build until it is listed in the test's table,
  whose behavior test then holds it to the dedupe. 3 of the 4 tests fail
  against the pre-fix engine.

## Validate rule for already-filed duplicates — not added

The DoD asked whether `goc validate` should also flag duplicates on
already-filed cards. Decided no, so no sibling card was filed:

- After this fix no goc verb writes a duplicate tag — `_cmd_new` is the
  only writer of `tags` — so one can only enter through a hand edit.
- There is no population to surface: a scan of all 823 cards on
  2026-10-30 found no repeated entry in `tags` or in any of the four
  edge lists.
- The engine already treats repeated list entries as a reader concern.
  The analogous `advances: [B, B]` case,
  [sort-tiebreak-double-counts-duplicate-advances-edges](../sort-tiebreak-double-counts-duplicate-advances-edges/),
  was fixed by counting distinct targets and left `goc validate`
  tolerant. A tags-only rule would break that symmetry, and a rule over
  all five list fields is a broader policy change than this card, with
  no observed duplicate to motivate it.

## Decision

*Resolved 2026-10-22T05:56:36Z:* Lower the gate: dedupe repeated --tag values the way advances are deduped

*Reasoning:* Bulk rule approved by the maintainer in a human session on 2026-10-22: a gated card with no written question and a mechanical fix drops to gate none

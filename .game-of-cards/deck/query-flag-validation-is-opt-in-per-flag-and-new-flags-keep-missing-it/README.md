---
title: query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it
summary: "Query-flag validation is bolted on one flag at a time (--tag, --status, --since each got their own guard card), so every unguarded flag silently returns wrong or empty output with exit 0: --advances/--advanced-by accept nonexistent titles, --board silently overrides --json with an ASCII grid, and --closed-since composes with a non-terminal --status or with --waiting into can-never-match queries. Meta-fix: one declared contract per query flag, enforced centrally, so a new flag without a contract fails closed."
status: open
stage: null
contribution: medium
created: "2026-07-11T01:24:14Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - invalid-status-filter-silently-empties-queue
  - invalid-tag-filter-silently-empties-queue
  - invalid-since-date-silently-empties-done-query
  - done-shortcut-overrides-status-filter
  - since-filter-without-done-hides-open-queue
tags: [bug, meta-fix, api-contract]
definition_of_done: |
  - [ ] PROCESS: mechanism decision recorded (option A/B/C below, plus error-vs-warn for unknown edge-filter titles) and gate lowered to none
  - [ ] TDD: reproduce.py exits zero — all five probes either hard-error or emit a diagnostic naming the offending flag/value
  - [ ] TDD: regression tests cover unknown --advances/--advanced-by title, --json + --board conflict, non-terminal --status + --closed-since, and --waiting + --closed-since
  - [ ] MECHANICAL: the instance table in this README is re-audited after the fix and every row reads "guarded"
  - [ ] PROCESS: a guard makes future query flags fail closed — adding a parser flag without a declared validation/conflict contract turns the suite red
---

# Query-flag validation is opt-in per flag, and new flags keep missing it

`goc`'s default (no-subcommand) query surface validates its flag inputs
and flag compositions one flag at a time. Five closed cards each added
one guard; every flag that never got its own card still resolves invalid
input or a contradictory composition silently — empty or wrong-format
output, exit 0.

## Location

- `goc/engine.py:2675` — `filter_cards` `--advances` / `--advanced-by`
  membership tests (no existence check on the queried title)
- `goc/engine.py:3763` — `_cmd_default` presentation dispatch
  (`if args.board: ... elif args.as_json: ...`)
- `goc/engine.py:3699` — status auto-extend for `--waiting` /
  `--closed-since` fires only when `--status` is unset; nothing checks
  the explicit-status or `--waiting`+`--closed-since` compositions

## What's broken

Three unguarded instances, confirmed on this deck (2026-07-11):

**1. `--advances` / `--advanced-by` accept a nonexistent card title.**
`filter_cards` (`goc/engine.py:2675`) tests membership only:

```python
if advances:
    out = [
        t
        for t in out
        if isinstance(t.frontmatter.get("advances"), list)
        and advances in t.frontmatter["advances"]
    ]
```

The queried title is never checked against `by_title` (already threaded
into `filter_cards` for the `ready` branch). A typo'd or since-renamed
title yields "no results", indistinguishable from "no edges". Contrast
`validate_tag_filters` (`goc/engine.py:2801`), which exits 2 with a
remedy for an unknown tag — and `compute_values`, which stderr-WARNs on
dangling `advances` edges in card frontmatter while the CLI filter for
the same edge field stays silent.

**2. `--board` silently overrides `--json`.** The presentation dispatch
(`goc/engine.py:3763`) is `if args.board: ... elif args.as_json: ...`,
so `goc --json --board` prints the ASCII kanban grid with exit 0 — a
machine consumer expecting JSON gets unparseable output. The repo's own
precedent for a flag conflict is a hard error
(`goc: error: pass only one of --done / --status`, exit 2, at
`goc/engine.py:3693`). Same-site symptom: `--slim` is read only inside
the `elif args.as_json` branch, so `goc --slim` without `--json` is a
silent no-op (its help text does say "With --json:", so that one is at
least documented).

**3. `--closed-since` composes into can-never-match queries.** The
status auto-extend (`goc/engine.py:3699`) fires only when
`args.status_flag is None`. With an explicit non-terminal status,
`goc --status open --closed-since 7d` requires `closed_at` set on an
open card — a state `goc validate` itself flags as incoherent — and
`goc --waiting --closed-since 24h` requires non-terminal ∧ closed.
Both print zero result rows with exit 0 on a deck that has both
impeded cards and recent closures.

## Empirical evidence

`uv run python .game-of-cards/deck/query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it/reproduce.py`:

```
[FAIL (silent, exit 0)] goc --advances no-such-card-xyz-reproduce
         exit=0  stdout[0]='ACTIVE: 4 claimed cards outside this open queue: support-external-game'
[FAIL (silent, exit 0)] goc --advanced-by no-such-card-xyz-reproduce
         exit=0  stdout[0]='ACTIVE: 4 claimed cards outside this open queue: support-external-game'
[FAIL (silent, exit 0)] goc --json --board
         exit=0  stdout[0]='OPEN                                                                  '
[FAIL (silent, exit 0)] goc --status open --closed-since 7d
         exit=0  stdout[0]='ACTIVE: 4 claimed cards outside this open queue: support-external-game'
[FAIL (silent, exit 0)] goc --waiting --closed-since 24h
         exit=0  stdout[0]='<no stdout>'

contrast (per-flag guards that DO exist):
  goc --tag no-such-tag           -> exit=2 stderr="goc: error: --tag: unknown tag 'no-such-tag' — add a project"
  goc --done --status open        -> exit=2 stderr='goc: error: pass only one of --done / --status'

DEFECT: 5/5 query-flag probes silently return wrong/empty output with exit 0
```

## Why it matters — this is the 6th–8th instance of one root-cause shape

The family is already catalogued, one card per flag, all closed:

| Instance | Card | Guard shape shipped |
|---|---|---|
| unknown `--status` value | [invalid-status-filter-silently-empties-queue](../invalid-status-filter-silently-empties-queue/) | argparse `choices` |
| unknown `--tag` value | [invalid-tag-filter-silently-empties-queue](../invalid-tag-filter-silently-empties-queue/) | `validate_tag_filters`, exit 2 |
| malformed `--since` date | [invalid-since-date-silently-empties-done-query](../invalid-since-date-silently-empties-done-query/) | `parse_since_filter`, exit 2 |
| `--done` ∧ `--status` conflict | [done-shortcut-overrides-status-filter](../done-shortcut-overrides-status-filter/) | explicit conflict error, exit 2 |
| `--since` without `--done` | [since-filter-without-done-hides-open-queue](../since-filter-without-done-hides-open-queue/) | explicit conflict error, exit 2 |
| unknown `--advances`/`--advanced-by` title | this card, instance 1 | **none** |
| `--json` ∧ `--board` conflict | this card, instance 2 | **none** |
| `--closed-since` ∧ non-terminal status / `--waiting` | this card, instance 3 | **none** |

Each fix so far guarded exactly the flag its card named, and the next
flag added to the parser (`--advances`/`--advanced-by`, `--board`,
`--closed-since`, `--waiting`) shipped with no guard. Per the audit
sibling-sweep rule, the 4th+ instance of a catalogued family files the
architectural meta-fix, not three more instance cards.

Reachability: all probes are plain CLI invocations of the default query
verb — the exact commands scripted consumers (CI dashboards, the
autonomous-loop skills, `goc --json` pipelines) already run. The
`--json --board` case corrupts a machine-read surface; the others
return "nothing matched" for queries that could never match anything.

## Decision required

Which mechanism replaces per-flag opt-in validation, and what severity
do unknown edge-filter titles get?

- **A — Central declarative flag-contract table.** Each query flag
  registers a contract (value validator; conflicts-with set; whether
  its argument must name an existing card). One pass in `_cmd_default`
  (after cards load, so title-existence checks are possible) enforces
  all contracts before filtering/rendering. A regression test walks the
  argparse parser and asserts every query flag has a contract entry —
  new flags fail closed. Most code, strongest guarantee; matches how
  the deck resolved the analogous families
  ([bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/),
  [draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it](../draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it/)).
- **B — argparse-native guards.** Mutually-exclusive group for
  `--board`/`--json`; `type=` validators where possible; a post-parse
  hook for deck-dependent checks (title existence). Less new machinery,
  but contracts stay scattered across the parser definition and the
  fail-closed property for future flags is weaker (nothing forces a new
  flag into a group or validator).
- **C — three more instance fixes.** Guard exactly the three instances
  above, no central mechanism. Cheapest now; the family history above
  is the argument against it.

Sub-decision for instance 1: hard error (exit 2, matching `--tag`) vs
stderr WARN + empty result (matching `compute_values`' dangling-edge
handling). Error is the family precedent; WARN keeps scripts that probe
for "does anything advance X?" working on renamed titles.

reproduce.py is fix-shape neutral: any probe that hard-errors OR emits
a diagnostic naming the offending flag/value counts as guarded.

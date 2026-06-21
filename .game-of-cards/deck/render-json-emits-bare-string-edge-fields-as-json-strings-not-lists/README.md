---
title: render-json-emits-bare-string-edge-fields-as-json-strings-not-lists
summary: "Eighth confirmed sibling of [[bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes]]. `render_json` (engine.py:2480-2483) reads the four edge fields with an `or []` fallback, which only catches `None` and empty containers; a truthy bare-string scalar like `advances: foo-card` passes through verbatim, so `goc --json` emits a string where the output contract promises a list. Close under whichever architectural fix the meta-fix adopts (loader reject / shared list-coercing helper / per-consumer guard)."
status: open
stage: null
contribution: medium
created: "2026-05-30T23:56:26Z"
closed_at: null
human_gate: decision
advances:
  - bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: this card is filed as the 8th confirmed sibling of [[bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes]]. Close it under whichever architectural approach the meta-fix decides on (A: loader rejects; B: centralized `_field_as_list` helper that `render_json` also routes through; C: per-consumer `isinstance(..., list)` guard at `engine.py:2480-2483`).
  - [ ] TDD: a regression test asserts `render_json` emits `[]` (or whatever the chosen architectural fix dictates) for a card whose `advances` / `advanced_by` / `supersedes` / `superseded_by` is a bare-string scalar — currently emits the bare string verbatim, breaking the JSON output contract.
  - [ ] MECHANICAL: implementation per the chosen approach. Under C, four lines at `engine.py:2480-2483` swap from `t.frontmatter.get(field) or []` to a list-coerced read.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
---

# `goc --json` emits bare-string edge fields as JSON strings, not lists

Eighth confirmed sibling of
[[bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes]]
— the meta-fix card explicitly predicted that "the next unguarded
read site will trigger the eighth filing" while Option C stays in
effect. This is that filing.

## What's broken

`render_json` (the implementation behind `goc --json` / `goc --ready
--json` / `goc --board --json`) builds each card's JSON record by
reading the four edge fields straight from the parsed frontmatter
with a falsy-fallback:

```python
# goc/engine.py:2480-2483
"advances": t.frontmatter.get("advances") or [],
"advanced_by": t.frontmatter.get("advanced_by") or [],
"supersedes": t.frontmatter.get("supersedes") or [],
"superseded_by": t.frontmatter.get("superseded_by") or [],
```

`or []` only catches `None` and empty containers. A bare-string
scalar like `advances: foo-card` (hand-edited or produced by an
unguarded writer — see siblings #2 and the closed
`goc-unadvance-rewrites-bare-string-edge-field-as-character-list`)
parses to a `str`, which is truthy, so the JSON output carries it
through verbatim:

```json
"advances": "foo-card",
"advanced_by": "bar-card",
```

instead of the expected list shape

```json
"advances": ["foo-card"],
"advanced_by": ["bar-card"],
```

Compare to the slim-mode branch one screen up (`engine.py:2457`,
`"tags": t.tags`), which uses the `Card.tags` property — already
hardened in the closed sibling
`tags-property-iterates-bare-string-tags-character-by-character`.
The asymmetry inside one function is the same shape as the asymmetry
the meta-fix card already cites between `_add_to_list_field` (guarded)
and `_remove_from_list_field` (unguarded).

## Reachability path

Any caller of `goc --json` consumes the broken shape:

- The `Skill(scan-deck)` `--json` flow (the slim-mode branch is safe;
  the full-mode branch is the affected path).
- External tooling that pipes `goc --json` into a downstream
  schema-validating consumer.
- The board renderer's `dependency_awaiting` / `awaiting` /
  `ready` derivations on the same record already route through
  `dependency_blocked` / `dependency_blockers` / `card_is_ready` —
  these are themselves part of the family and were patched in closed
  sibling #3.

Trigger input: any card in the loaded deck whose `advances` /
`advanced_by` / `supersedes` / `superseded_by` frontmatter field is
a bare scalar (not a YAML list). This happens whenever the writer
side is unguarded (see closed sibling #6 and the still-open
`_remove_from_list_field` site) or a human hand-edits.

## Reproducer

`reproduce.py` (next to this README) builds a tempdir deck with one
card carrying `advances: foo-card` (bare string), invokes
`render_json` directly, and asserts the JSON record has `advances:
"foo-card"` (string) — failing the falsifiable prediction that the
output should be a list.

## Why it matters

Two things:

1. **JSON output contract.** The schema downstream consumers
   reasonably expect is "the four edge fields are lists." A bare
   string slips through the contract silently.
2. **Meta-fix evidence.** The Option-C "doesn't retire the family"
   warning on the parent card has now materialised — eight sites
   total, six closed-fixed and two open. Each new read-time site
   doubles surface area on review. This card is the trigger to pick
   Option A or B over C.

## Decision required

This card inherits the parent's open architectural choice. Resolve
it on the parent card, not here:

- Pick approach A or B (loader-side fix) on
  [[bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes]];
  this card and the other open sibling close as side-effects of the
  same patch.
- Or pick approach C and accept that the meta-fix card stays open as
  a register for future sightings.

Do not implement a stand-alone `isinstance(..., list)` guard at
`engine.py:2480-2483` without first reconciling the architectural
choice on the parent card — that's exactly the per-consumer pattern
the meta-fix card is trying to retire.

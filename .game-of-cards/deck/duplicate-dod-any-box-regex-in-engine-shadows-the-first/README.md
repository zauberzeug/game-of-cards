---
title: duplicate-dod-any-box-regex-in-engine-shadows-the-first
summary: "`goc/engine.py` defines `DOD_ANY_BOX` at line 464 and again, byte-identical, at line 480. The second assignment silently shadows the first; an edit to one is a no-op until the duplicate is also touched. Two independent commits each introduced one definition without noticing the other. No current behavioral bug, but it's a documented trap for future regex edits (e.g. adding `re.MULTILINE` to align with sibling `DOD_OPEN_BOX` / `DOD_DONE_BOX`)."
status: done
stage: null
contribution: medium
created: "2026-05-29T17:25:26Z"
closed_at: "2026-05-29T17:29:43Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix]
definition_of_done: |
  - [x] MECHANICAL: the second `DOD_ANY_BOX = re.compile(...)` assignment in `goc/engine.py` is deleted; only the first (with its comment block) remains.
  - [x] TDD: a regression test asserts `goc.engine` source contains exactly one `DOD_ANY_BOX = re.compile` line, so a future re-introduction trips the suite.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` is green.
  - [x] PROCESS: `uv run goc validate` is clean.
worker: {who: "claude[bot]", where: main}
---

# Duplicate `DOD_ANY_BOX` regex in engine — second definition shadows the first

## Location

`goc/engine.py:464` and `goc/engine.py:480` — two module-level
assignments of the same name to byte-identical compiled regexes.

## What's broken

`DOD_ANY_BOX` is defined twice. Both lines compile the same pattern:

```python
# goc/engine.py:460-464
DOD_OPEN_BOX = re.compile(r"^[ \t]*- \[ \]", re.MULTILINE)
DOD_DONE_BOX = re.compile(r"^[ \t]*- \[x\]", re.MULTILINE | re.IGNORECASE)
# Matches any DoD checkbox line (open or checked), case-insensitive so it
# agrees with DOD_OPEN_BOX + DOD_DONE_BOX on the same `[X]`/`[x]` set.
DOD_ANY_BOX = re.compile(r"^[ \t]*- \[[ xX]\]")
```

```python
# goc/engine.py:479-483
DOD_METHOD_TAGS = ("TDD", "EMPIRICAL", "MECHANICAL", "PROCESS")
DOD_ANY_BOX = re.compile(r"^[ \t]*- \[[ xX]\]")
DOD_TAGGED_BOX = re.compile(
    r"^[ \t]*- \[[ xX]\] (?:" + "|".join(DOD_METHOD_TAGS) + r"): "
)
```

The second assignment rebinds the name; Python's module-level execution
order means whichever line runs last wins, and from that point on every
reader of `DOD_ANY_BOX` sees the line-480 object.

## How it got here (git archaeology)

Two independent commits each added one of the definitions; neither
noticed the other was about to do the same:

- `0fb8a7a feat(engine/validate): warn on untagged DoD items by method
  class` introduced `DOD_METHOD_TAGS` + `DOD_ANY_BOX` + `DOD_TAGGED_BOX`
  as a single block (now lines 479–483).
- `11bdb6b fix(engine): reconcile DoD box indexing for uppercase [X]
  boxes` introduced `DOD_ANY_BOX` next to the existing `DOD_OPEN_BOX` /
  `DOD_DONE_BOX` constants with its own clarifying comment (now lines
  462–464), apparently unaware of the prior block sixteen lines later.

The comment on line 462–463 is the canonical home for the constant —
it sits with its siblings and explains *why* the regex is
case-insensitive. The line-480 definition is the duplicate that should
go.

## Why it matters

No current behavioral defect — both compile the same pattern and the
shadowing is a no-op. But the trap is real for any future edit:

- A maintainer fixing `DOD_ANY_BOX` at line 464 (e.g. adding
  `re.MULTILINE` so it agrees with `DOD_OPEN_BOX` / `DOD_DONE_BOX`,
  which is the pattern the sibling constants follow but `DOD_ANY_BOX`
  does NOT — see line 480: no flags) will discover the change silently
  has no effect, because the line-480 rebind wins.
- Code review of either commit could have caught it, but the
  twin-definition shape is exactly the kind of cross-cutting drift a
  diff reviewer scans past.
- The constant is consumed by `_dod_box_indices` (line 473) and
  `untagged_dod_items` (defined later), so DoD-rewrite and DoD-tag
  validation both run through this regex; a future edit that needed
  `re.MULTILINE` would land in the wrong cell.

This is an architectural smell, not a bug today, and the fix is purely
mechanical — `--gate none` work.

## Fix

Delete the assignment on line 480, leaving the canonical definition at
line 464 (which has the explanatory comment and sits with its siblings)
as the sole binding. `DOD_TAGGED_BOX` at line 481 keeps its position;
only the redundant `DOD_ANY_BOX` line 480 is removed.

Add a one-line regression test (e.g. `tests/test_engine_module_singletons.py`
or appended to an existing test module) that reads the source of
`goc/engine.py` and asserts `re.findall(r"^DOD_ANY_BOX = re\.compile",
src, re.MULTILINE)` has length 1, so a future re-introduction trips the
suite.

## Reachability path

This is a code-organization defect, not a runtime defect, so there's no
input shape that produces it — the rebind happens at module import.
Reachability is "anyone imports `goc.engine`," which is every CLI
invocation and every test run. The defect is reached the moment a
maintainer edits one definition expecting the change to take effect.

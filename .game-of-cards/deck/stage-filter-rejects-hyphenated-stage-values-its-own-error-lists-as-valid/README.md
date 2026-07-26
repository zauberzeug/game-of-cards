---
title: stage-filter-rejects-hyphenated-stage-values-its-own-error-lists-as-valid
summary: "`parse_stage_filter` (goc/engine.py:2738) tests `\"-\" in stage_flag` BEFORE exact-membership, so any stage enum value containing a hyphen is unconditionally parsed as a range and rejected — while the rejection message lists that very value among the valid choices. Latent on the shipped enum ([null, alpha, beta, stable], no hyphens); reachable the moment stage_values becomes project-configurable, which is the subject of the open support-custom-card-workflows-and-statuses story."
status: open
stage: null
contribution: low
created: "2026-07-26T19:13:51Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — with a hyphenated value in `STAGE_ORDER`, `--stage <that-value>` resolves to `[<that-value>]`
  - [ ] TDD: range parsing still works — `--stage alpha-stable` returns the inclusive span, and an unknown `--stage nope-alpha` still exits 2
  - [ ] MECHANICAL: `parse_stage_filter` tests exact membership in `STAGE_ORDER` before the `"-" in stage_flag` range branch
  - [ ] PROCESS: `uv run goc validate` passes and the regression suite stays green
---

# `--stage` rejects a hyphenated stage value while listing it as valid

## Location

`goc/engine.py:2734-2748` (`parse_stage_filter`):

```python
def parse_stage_filter(stage_flag: str | None) -> list[str] | None:
    if not stage_flag:
        return None
    valid = ", ".join(STAGE_ORDER)
    if "-" in stage_flag:                      # <-- range branch runs FIRST
        a, b = stage_flag.split("-", 1)
        if a not in STAGE_ORDER or b not in STAGE_ORDER:
            print(f"goc: error: --stage: expected one of {valid}, or a range like alpha-stable", file=sys.stderr)
            sys.exit(2)
        ...
    if stage_flag not in STAGE_ORDER:          # <-- exact match never reached
        ...
    return [stage_flag]
```

## What's broken

The range branch is tested before exact membership, so the two syntaxes are
not disambiguated — they are ordered, with range winning. Any stage enum
value containing a hyphen is therefore unreachable: `pre-alpha` splits to
`("pre", "alpha")`, `"pre"` is not a stage, and the call exits 2.

The diagnostic then contradicts itself. `valid` is built from the whole
enum, so the rejection message lists the exact value the user just passed:

```
$ goc --stage pre-alpha
goc: error: --stage: expected one of null, pre-alpha, alpha, beta, stable, or a range like alpha-stable
```

A user reading that has no way to act on it — the tool names `pre-alpha` as
an accepted choice in the same breath as refusing it.

`STAGE_ORDER` is derived from the schema, not hardcoded
(`goc/engine.py:2320`), which is what makes this a contract bug rather than a
typo: the function does not honor the enum it advertises.

## Empirical evidence

`uv run python .game-of-cards/deck/stage-filter-rejects-hyphenated-stage-values-its-own-error-lists-as-valid/reproduce.py`:

```
=== shipped stage enum (goc/schema.yaml) ===
STAGE_ORDER = ['null', 'alpha', 'beta', 'stable']
no hyphenated value today -> the defect is latent, not live

=== with a hyphenated enum value: ['null', 'pre-alpha', 'alpha', 'beta', 'stable'] ===
--stage 'pre-alpha'    -> exit 2
                          goc: error: --stage: expected one of null, pre-alpha, alpha, beta, stable, or a range like alpha-stable
--stage 'alpha'        -> ['alpha']
--stage 'alpha-stable' -> ['alpha', 'beta', 'stable']

=== verdict ===
FAIL: --stage 'pre-alpha' rejected although 'pre-alpha' is in the enum
FAIL: ...and the rejection message lists 'pre-alpha' as a valid choice
```

Exit 1.

## Why it matters — and why this is filed low

**Latent, not live.** The shipped enum is
`stage_values: [null, alpha, beta, stable]` (`goc/schema.yaml:24`) — no
hyphens — so no consumer can trigger this against a stock install today. It
is filed because the trigger is one schema edit away, not because anyone is
hitting it now.

**Reachability path.** `STAGE_ORDER` is computed at import from
`_ENUM_SCHEMA.stage_values`, i.e. read from `goc/schema.yaml`. The open story
[support-custom-card-workflows-and-statuses](../support-custom-card-workflows-and-statuses/)
is specifically about letting a consuming repo supply its own enums; the
moment it lands, `pre-alpha` / `needs-review` / `in-design` become natural
stage names, and each one silently loses `--stage` addressability. Fixing the
ordering now costs one line and removes a trap from that story's path.
Hyphenated *status* values are unaffected — `--status` is an argparse
`choices=` list with no range syntax.

## Fix

Move the exact-membership test above the range branch in
`goc/engine.py:2738` — try the whole argument as a stage name first, and only
fall through to `a-b` range parsing when it is not itself an enum member:

```python
if stage_flag in STAGE_ORDER:
    return [stage_flag]
if "-" in stage_flag:
    ...
```

Exact-match-first is also the disambiguation a reader expects: a literal enum
value beats a syntactic interpretation of the same string. Ranges keep
working because no shipped or plausible stage name equals an `a-b` pair of
other stage names; if one ever did, the enum member is the right winner.

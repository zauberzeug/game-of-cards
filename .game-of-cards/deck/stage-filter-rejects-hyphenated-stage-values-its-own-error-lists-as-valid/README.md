---
title: stage-filter-rejects-hyphenated-stage-values-its-own-error-lists-as-valid
summary: "`parse_stage_filter` (goc/engine.py:2738) tests `\"-\" in stage_flag` BEFORE exact-membership, so any stage enum value containing a hyphen is unconditionally parsed as a range and rejected — while the rejection message lists that very value among the valid choices. Latent on the shipped enum ([null, alpha, beta, stable], no hyphens); reachable the moment stage_values becomes project-configurable, which is the subject of the open support-custom-card-workflows-and-statuses story."
status: done
stage: null
contribution: low
created: "2026-07-26T19:13:51Z"
closed_at: "2026-07-26T21:42:33Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — with a hyphenated value in `STAGE_ORDER`, `--stage <that-value>` resolves to `[<that-value>]`
  - [x] TDD: range parsing still works — `--stage alpha-stable` returns the inclusive span, and an unknown `--stage nope-alpha` still exits 2
  - [x] MECHANICAL: `parse_stage_filter` tests exact membership in `STAGE_ORDER` before the `"-" in stage_flag` range branch
  - [x] PROCESS: `uv run goc validate` passes and the regression suite stays green
worker: {who: "claude[bot]", where: main}
---

# `--stage` rejects a hyphenated stage value while listing it as valid

## Location

`goc/engine.py:2734-2751` (`parse_stage_filter`), in its pre-fix shape:

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
--stage 'pre-alpha'    -> ['pre-alpha']
--stage 'alpha'        -> ['alpha']
--stage 'alpha-stable' -> ['alpha', 'beta', 'stable']

=== verdict ===
PASS: hyphenated enum values are addressable through --stage
```

Exit 0. Before the fix, the same probe printed `--stage 'pre-alpha' -> exit 2`
followed by the self-contradicting diagnostic quoted above, and failed twice:

```
FAIL: --stage 'pre-alpha' rejected although 'pre-alpha' is in the enum
FAIL: ...and the rejection message lists 'pre-alpha' as a valid choice
```

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

## Fix (applied)

The exact-membership test now runs above the range branch in
`goc/engine.py:2734-2751` — the whole argument is tried as a stage name first,
and only falls through to `a-b` range parsing when it is not itself an enum
member:

```python
    if stage_flag in STAGE_ORDER:
        return [stage_flag]
    valid = ", ".join(STAGE_ORDER)
    if "-" in stage_flag:
        ...
```

The old trailing `if stage_flag not in STAGE_ORDER` guard collapsed into the
unconditional error at the end of the function, since a non-member with no
hyphen can only be a usage error.

Exact-match-first is also the disambiguation a reader expects: a literal enum
value beats a syntactic interpretation of the same string. Ranges keep working
because no shipped or plausible stage name equals an `a-b` pair of other stage
names; if one ever did, the enum member is the right winner.

Regression coverage lives in `tests/test_stage_filter.py`
(`test_hyphenated_enum_value_is_addressable`,
`test_range_and_rejection_survive_exact_match_first`), which drive
`STAGE_ORDER` with a hyphenated enum the shipped schema does not yet produce.

**Residual gap, tracked separately.** "Ranges keep working" holds for a range
over hyphen-free endpoints, which is what this card's DoD tested. A range whose
*left* endpoint is itself hyphenated (`pre-alpha-stable`) still fails, because
the range branch splits on the first hyphen before consulting the enum — filed
as
[stage-range-with-hyphenated-left-endpoint-is-unreachable](../stage-range-with-hyphenated-left-endpoint-is-unreachable/).

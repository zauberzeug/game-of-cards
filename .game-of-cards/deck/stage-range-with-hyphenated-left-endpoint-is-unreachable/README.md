---
title: stage-range-with-hyphenated-left-endpoint-is-unreachable
summary: "`parse_stage_filter` splits a `--stage a-b` range on the FIRST hyphen (`goc/engine.py:2745`), so a span whose left endpoint is itself a hyphenated stage value cannot be spelled: `pre-alpha-stable` reads as (`pre`, `alpha-stable`) and exits 2, while the mirror span `null-pre-alpha` works because the hyphenated value happens to land in the right half. Latent on the shipped hyphen-free enum; reachable via the same path as its already-fixed sibling — project-supplied `stage_values`."
status: open
stage: null
contribution: low
created: "2026-07-26T21:39:32Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — with `pre-alpha` in `STAGE_ORDER`, `--stage pre-alpha-stable` resolves to the full span and `null-pre-alpha` / `alpha-stable` / `pre-alpha` keep their current results
  - [ ] TDD: an argument with no valid split still exits 2 (`nope-alpha`, `alpha-nope`), and an argument with two or more valid splits exits 2 naming the ambiguity rather than silently picking one
  - [ ] MECHANICAL: the range branch resolves its split position against `STAGE_ORDER` instead of hardcoding `split("-", 1)`
  - [ ] PROCESS: `uv run goc validate` passes and the regression suite stays green
---

# A `--stage` range whose left endpoint is hyphenated cannot be spelled

## Location

`goc/engine.py:2734-2751` (`parse_stage_filter`), the range branch:

```python
    if "-" in stage_flag:
        a, b = stage_flag.split("-", 1)       # <-- split position is arbitrary
        if a not in STAGE_ORDER or b not in STAGE_ORDER:
            print(f"goc: error: --stage: expected one of {valid}, or a range like alpha-stable", file=sys.stderr)
            sys.exit(2)
```

## What's broken

`split("-", 1)` picks the leftmost hyphen unconditionally, so the split point
is chosen before the enum is consulted. With a hyphenated stage value in the
enum, that makes exactly one half of the range syntax usable:

| span | spelled | first-hyphen split | result |
|---|---|---|---|
| `pre-alpha` .. `stable` | `pre-alpha-stable` | (`pre`, `alpha-stable`) | exit 2 — **unspellable** |
| `null` .. `pre-alpha` | `null-pre-alpha` | (`null`, `pre-alpha`) | works by luck |

The two rows differ only in which side the hyphenated value sits on. A range
operator whose reachability depends on that is not resolving its own grammar.

The sibling card
[stage-filter-rejects-hyphenated-stage-values-its-own-error-lists-as-valid](../stage-filter-rejects-hyphenated-stage-values-its-own-error-lists-as-valid/)
fixed the *single-value* half of this by testing exact enum membership before
the range branch, and reasoned that "ranges keep working because no shipped or
plausible stage name equals an `a-b` pair of other stage names". That holds for
a whole-argument collision — which is exactly what exact-match-first settles —
but not for an endpoint collision, which is what this card is about. Its DoD
tested `alpha-stable`, a range over two hyphen-free values, so the gap survived
that closure.

## Empirical evidence

`uv run python .game-of-cards/deck/stage-range-with-hyphenated-left-endpoint-is-unreachable/reproduce.py`:

```
=== shipped stage enum (goc/schema.yaml) ===
STAGE_ORDER = ['null', 'alpha', 'beta', 'stable']
no hyphenated value today -> the defect is latent, not live

=== with a hyphenated enum value: ['null', 'pre-alpha', 'alpha', 'beta', 'stable'] ===
--stage 'pre-alpha-stable'   -> 'exit 2'                                   want ['pre-alpha', 'alpha', 'beta', 'stable']   FAIL
--stage 'null-pre-alpha'     -> ['null', 'pre-alpha']                      want ['null', 'pre-alpha']   ok
--stage 'alpha-stable'       -> ['alpha', 'beta', 'stable']                want ['alpha', 'beta', 'stable']   ok
--stage 'pre-alpha'          -> ['pre-alpha']                              want ['pre-alpha']   ok
--stage 'nope-alpha'         -> 'exit 2'                                   want 'EXIT2'   ok
--stage 'alpha-nope'         -> 'exit 2'                                   want 'EXIT2'   ok

=== verdict ===
FAIL: --stage 'pre-alpha-stable' gave 'exit 2', want ['pre-alpha', 'alpha', 'beta', 'stable']
```

Exit 1.

## Why it matters — and why this is filed low

**Latent, not live.** `stage_values: [null, alpha, beta, stable]`
(`goc/schema.yaml:24`) has no hyphens, so on a stock install every argument has
at most one candidate split and the first-hyphen shortcut is indistinguishable
from resolving properly. No consumer can hit this today.

**Reachability path.** `STAGE_ORDER` is computed at import from
`_ENUM_SCHEMA.stage_values`, i.e. read from `goc/schema.yaml`. The open story
[support-custom-card-workflows-and-statuses](../support-custom-card-workflows-and-statuses/)
is about letting a consuming repo supply its own enums; `pre-alpha`,
`needs-review`, `in-design` are the natural first hyphenated stage names, and
each one becomes a valid *endpoint* the range syntax cannot address from the
left. Fixing the split resolution now removes the second half of a trap on that
story's path — the first half is already closed by the sibling card.

## Fix

Resolve the split against the enum instead of hardcoding the position: collect
every hyphen index whose two halves are BOTH in `STAGE_ORDER`, then

- exactly one candidate → that is the range (this is every case the shipped
  enum can produce, so current behavior is preserved bit-for-bit);
- zero candidates → the existing "expected one of …, or a range like
  alpha-stable" error, exit 2;
- two or more candidates → a distinct error naming the ambiguity and listing
  the candidate spans, exit 2.

Sketch, replacing the `split("-", 1)` line:

```python
    candidates = [
        (head, tail)
        for i, ch in enumerate(stage_flag)
        if ch == "-"
        for head, tail in [(stage_flag[:i], stage_flag[i + 1 :])]
        if head in STAGE_ORDER and tail in STAGE_ORDER
    ]
```

The >1 branch cannot fire on any hyphen-free enum, and needs a contrived one to
fire at all (a value spelled exactly `X-Y` where `X` and `Y` are also values).
It is still worth writing rather than letting the leftmost candidate win
silently: this deck consistently treats "silently picks one reading of an
ambiguous input" as the defect rather than the fix — see
[yaml-lite-overindented-block-sequence-item-silently-absorbed-instead-of-raising](../yaml-lite-overindented-block-sequence-item-silently-absorbed-instead-of-raising/)
and
[yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising](../yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising/).
Raising keeps that convention intact, and a user who hits it can always pass the
two endpoints another way.

Exact-match-first stays ahead of all of this, so a hyphenated value that is
itself a whole enum member is never reinterpreted as a range.

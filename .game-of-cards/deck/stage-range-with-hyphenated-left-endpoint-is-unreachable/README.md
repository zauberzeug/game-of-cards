---
title: stage-range-with-hyphenated-left-endpoint-is-unreachable
summary: "`parse_stage_filter` splits a `--stage a-b` range on the FIRST hyphen (`goc/engine.py:2745`), so a span whose left endpoint is itself a hyphenated stage value cannot be spelled: `pre-alpha-stable` reads as (`pre`, `alpha-stable`) and exits 2, while the mirror span `null-pre-alpha` works because the hyphenated value happens to land in the right half. Latent on the shipped hyphen-free enum; reachable via the same path as its already-fixed sibling — project-supplied `stage_values`."
status: done
stage: null
contribution: low
created: "2026-07-26T21:39:32Z"
closed_at: "2026-07-26T21:46:36Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — with `pre-alpha` in `STAGE_ORDER`, `--stage pre-alpha-stable` resolves to the full span and `null-pre-alpha` / `alpha-stable` / `pre-alpha` keep their current results
  - [x] TDD: an argument with no valid split still exits 2 (`nope-alpha`, `alpha-nope`), and an argument with two or more valid splits exits 2 naming the ambiguity rather than silently picking one
  - [x] MECHANICAL: the range branch resolves its split position against `STAGE_ORDER` instead of hardcoding `split("-", 1)`
  - [x] PROCESS: `uv run goc validate` passes and the regression suite stays green
worker: {who: "claude[bot]", where: main}
---

# A `--stage` range whose left endpoint is hyphenated cannot be spelled

## Location

`goc/engine.py:2734-2764` (`parse_stage_filter`), the range branch in its
pre-fix shape:

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
--stage 'pre-alpha-stable'   -> ['pre-alpha', 'alpha', 'beta', 'stable']   want ['pre-alpha', 'alpha', 'beta', 'stable']   ok
--stage 'null-pre-alpha'     -> ['null', 'pre-alpha']                      want ['null', 'pre-alpha']   ok
--stage 'alpha-stable'       -> ['alpha', 'beta', 'stable']                want ['alpha', 'beta', 'stable']   ok
--stage 'pre-alpha'          -> ['pre-alpha']                              want ['pre-alpha']   ok
--stage 'nope-alpha'         -> 'exit 2'                                   want 'EXIT2'   ok
--stage 'alpha-nope'         -> 'exit 2'                                   want 'EXIT2'   ok

=== with an enum that makes one argument ambiguous: ['null', 'alpha', 'beta', 'alpha-beta', 'beta-stable', 'stable'] ===
--stage 'alpha-beta-stable'  -> 'exit 2'                                   want 'EXIT2'   ok

=== verdict ===
PASS: every span over the enum is expressible, ambiguity is reported
```

Exit 0. Before the fix the same probe failed twice — the unspellable span, and
the silent guess on the ambiguous argument:

```
FAIL: --stage 'pre-alpha-stable' gave 'exit 2', want ['pre-alpha', 'alpha', 'beta', 'stable']
FAIL: --stage 'alpha-beta-stable' gave ['alpha', 'beta', 'alpha-beta', 'beta-stable'], want 'EXIT2'
```

The second line is the one worth reading twice: pre-fix, an argument with two
valid readings did not error — it returned one of them, chosen by where the
first hyphen happened to fall.

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

## Fix (applied)

The split is resolved against the enum instead of hardcoded: every hyphen index
whose two halves are BOTH in `STAGE_ORDER` becomes a candidate span, and the
count decides:

- exactly one candidate → that is the range (this is every case the shipped enum
  can produce, so current behavior is preserved bit-for-bit);
- zero candidates → the existing "expected one of …, or a range like
  alpha-stable" error, exit 2;
- two or more candidates → a distinct error naming the ambiguity and both
  readings, exit 2.

`goc/engine.py:2737-2764`:

```python
    spans = [
        (stage_flag[:i], stage_flag[i + 1 :])
        for i, ch in enumerate(stage_flag)
        if ch == "-" and stage_flag[:i] in STAGE_ORDER and stage_flag[i + 1 :] in STAGE_ORDER
    ]
    if len(spans) > 1:
        readings = " and ".join(f"{a!r}..{b!r}" for a, b in spans)
        print(
            f"goc: error: --stage: {stage_flag!r} is an ambiguous range — it reads as {readings}",
            file=sys.stderr,
        )
        sys.exit(2)
```

The >1 branch cannot fire on any hyphen-free enum, and needs a contrived one to
fire at all (a value spelled exactly `X-Y` where `X` and `Y` are also values).
It is still written rather than letting the leftmost candidate win silently:
this deck consistently treats "silently picks one reading of an ambiguous input"
as the defect rather than the fix — see
[yaml-lite-overindented-block-sequence-item-silently-absorbed-instead-of-raising](../yaml-lite-overindented-block-sequence-item-silently-absorbed-instead-of-raising/)
and
[yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising](../yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising/).
The diagnostic names both readings so a consumer can see which two of their own
stage values overlap; renaming one of them is the remedy, since `--stage` takes a
single argument and has no alternate spelling for a span.

Exact-match-first (from the sibling card) stays ahead of all of this, so a
hyphenated value that is itself a whole enum member is never reinterpreted as a
range.

Regression coverage: `tests/test_stage_filter.py`
(`test_range_over_hyphenated_left_endpoint_is_spellable`,
`test_ambiguous_range_is_reported_not_guessed`).

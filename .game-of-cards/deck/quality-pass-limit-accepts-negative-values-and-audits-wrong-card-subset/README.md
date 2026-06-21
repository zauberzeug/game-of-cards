---
title: quality-pass-limit-accepts-negative-values-and-audits-wrong-card-subset
status: done
stage: null
contribution: medium
created: "2026-06-20T05:20:50Z"
closed_at: "2026-06-20T05:25:20Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (a negative `--limit` is rejected at the argparse layer with the same `is not a non-negative integer` error `--max-rows` already produces)
  - [x] TDD: parsing `quality-pass --limit 0` and `--limit 3` still succeeds (non-negative values unaffected)
  - [x] MECHANICAL: `--limit` declaration at `engine.py:3075` uses `type=_non_negative_int`
  - [x] `uv run python -m unittest discover -s tests` passes
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `quality-pass --limit` accepts negative values and audits the wrong card subset

## Summary

`goc quality-pass --limit` is declared `type=int`, so a negative value
passes argparse and flows into a Python slice `cards[:limit]`. Instead
of capping the audited card count, `--limit -2` drops the *last two*
cards and audits everything else, and `--limit 0` silently audits zero.
The structurally-identical `--max-rows` flag was already hardened with
`_non_negative_int`; `--limit` is the missed sibling.

## Location

- Declaration: `goc/engine.py:3075`
- Slice that consumes it: `goc/engine.py:3704`
- Helper that should be used: `goc/engine.py:2994` (`_non_negative_int`)
- Precedent already applied to a peer flag: `goc/engine.py:3056` (`--max-rows`)

## What's broken

The `--limit` flag is declared with the unconstrained int converter:

```python
# goc/engine.py:3075
p_qp.add_argument("--limit", type=int, default=None,
                  help="With --llm: cap card count (testing/sampling).")
```

and the value is consumed by a bare slice:

```python
# goc/engine.py:3704
sample = cards if limit is None else cards[:limit]
```

The help text says "cap card count" — a count is non-negative. But
`cards[:limit]` is a valid Python slice for negative bounds, so a
negative `--limit` does not cap; it removes cards from the *end* of the
list and audits the rest. `--limit 0` audits nothing.

The sibling flag `--max-rows` already guards against exactly this with
the existing helper:

```python
# goc/engine.py:2994
def _non_negative_int(value: str) -> int:
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError(f"{value!r} is not a non-negative integer")
    return n

# goc/engine.py:3056
parser.add_argument("--max-rows", type=_non_negative_int, default=20, ...)
```

So the project has already decided that count-style flags reject
negatives — `--limit` was simply left on the old `type=int`.

## Empirical evidence

```
$ uv run goc --board --max-rows -1
goc: error: argument --max-rows: '-1' is not a non-negative integer   # peer flag rejects

$ python3 -c "lst=['a','b','c','d','e']; print(lst[:-2]); print(lst[:0])"
['a', 'b', 'c']   # --limit -2 keeps the first 3, drops the last 2
[]                # --limit 0 audits nothing
```

`uv run goc quality-pass --limit -2` is accepted at the argparse layer
(no error) and would feed a silently-truncated card set into the
Sonnet audit. See `reproduce.py` for an executable proof.

## Why it matters

`quality-pass --llm` runs an LLM audit over a sampled card set. A
negative or zero `--limit` — a plausible typo or off-by-one in a test
/ sampling invocation — does not fail loudly; it audits a different,
unexpected subset (or none), so a reviewer believes they sampled N
cards from the front when they actually skipped the tail or audited
nothing. The reachability path is direct: any operator or script
passing `--limit <neg>` on the CLI reaches the slice at line 3704
unguarded.

## Fix

Change the declaration at `engine.py:3075` to reuse the existing
helper, mirroring `--max-rows`:

```python
p_qp.add_argument("--limit", type=_non_negative_int, default=None,
                  help="With --llm: cap card count (testing/sampling).")
```

One-token change; no design decision — the project already ruled that
count flags reject negatives (closed card
[negative-board-row-limit-hides-cards](../negative-board-row-limit-hides-cards/)).

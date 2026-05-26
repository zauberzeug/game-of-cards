---
title: frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values
summary: "`_yaml_inline` quotes a scalar only when `_YAML_NEEDS_QUOTE` matches or the value is in `_YAML_RESERVED` (the lowercase set `{null,true,false,yes,no}`). But the vendored parser ALSO coerces integer-looking strings (`_INT_RE`), the full null set (`null/Null/NULL/~`), and case-variant booleans (`True/TRUE/Yes/NO/...`). A string field holding any of these is emitted bare and re-parsed as int / None / bool — silent type-loss on the emit->parse round-trip."
status: active
stage: null
contribution: high
created: "2026-05-26T20:53:28Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — integer-looking, null-variant, and case-variant-boolean string values all survive an emit->parse round-trip unchanged (`data == fm`).
  - [ ] TDD: the quote-trigger predicate quotes a value the parser would coerce to int (`_INT_RE`), to null (full `_NULL_SET`: `null/Null/NULL/~`), or to bool (full `_TRUE_SET`/`_FALSE_SET`, including case variants).
  - [ ] MECHANICAL: fix lands in `goc/engine.py` (`_yaml_inline` / its quote-trigger predicate) and derives the keyword/int recognition from the parser's own sets rather than the hand-maintained lowercase `_YAML_RESERVED`, so the two truth-sets cannot drift again.
  - [ ] TDD: no behavior change for values that already round-trip bare (plain prose, already-quoted reserved words) and for genuine int/bool/None Python values (which must still emit bare, not quoted).
  - [ ] TDD: `uv run goc validate` passes on this repo's deck.
worker: {who: "claude[bot]", where: main}
---

# Frontmatter emitter doesn't quote integer-, null-, or case-variant-boolean-looking string values

## Location

`goc/engine.py:168` — `_YAML_RESERVED = {"null", "true", "false", "yes", "no"}`
— consumed by the quote-trigger predicate in `_yaml_inline` at
`goc/engine.py:192-203`.

## What's broken

`emit_frontmatter` writes a scalar bare unless the quote-trigger
predicate fires:

```python
_YAML_RESERVED = {"null", "true", "false", "yes", "no"}
...
def _yaml_inline(value) -> str:
    ...
    s = str(value)
    if (
        _YAML_NEEDS_QUOTE.search(s)
        or s in _YAML_RESERVED
        or s in _YAML_BLOCK_TOKENS
        or (s and s[0] in _YAML_INDICATOR_FIRST)
        or s != s.strip()
    ):
        ...quote...
    return s
```

The predicate's keyword check (`s in _YAML_RESERVED`) is a strict
**lowercase-only subset** of what the vendored parser coerces. The
parser (`goc/_vendor/yaml_lite.py:34-38`) recognizes more:

```python
_DATE_RE  = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_INT_RE   = re.compile(r"^-?\d+$")
_NULL_SET = frozenset(("null", "Null", "NULL", "~"))
_TRUE_SET = frozenset(("true", "True", "TRUE", "yes", "Yes", "YES"))
_FALSE_SET = frozenset(("false", "False", "FALSE", "no", "No", "NO"))
```

So a string field (`summary`, `title`, `waiting_until`, `worker.who`,
`worker.where`) whose value is `"123"`, `"~"`, `"NULL"`, `"True"`,
`"Yes"`, `"NO"`, etc. is emitted bare and re-parsed as `int` / `None`
/ `bool` — silent type-loss. The emit->parse round-trip is not closed.

This is the same root-cause shape as the **closed** card
[frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values](../frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values/),
whose own framing called the predicate "an under-specified subset of
values the parser will not round-trip bare." That card fixed only the
indicator-leading (`*`/`&`) and whitespace-padded facets; it explicitly
did **not** cover int / null-variant / case-variant-boolean coercion.
Two independently-maintained truth-sets for "what is a bare keyword"
(`_YAML_RESERVED` in the emitter vs. the parser's three sets +
`_INT_RE`) are the structural reason this keeps recurring — the fix
should derive the emitter's recognition from the parser's sets.

## Empirical evidence

`reproduce.py` output (exit 1 = defect fires):

```
LOSS: summary='123'          -> 123 (int)
LOSS: summary='02'           -> 2 (int)
LOSS: summary='-5'           -> -5 (int)
LOSS: summary='~'            -> None (NoneType)
LOSS: summary='NULL'         -> None (NoneType)
LOSS: summary='Null'         -> None (NoneType)
LOSS: summary='True'         -> True (bool)
LOSS: summary='TRUE'         -> True (bool)
LOSS: summary='Yes'          -> True (bool)
LOSS: summary='NO'           -> False (bool)
LOSS: summary='FALSE'        -> False (bool)
OK  : summary='2026-01-01'   -> '2026-01-01' (str)
```

11 of 12 string values change type on a single emit->parse round-trip.

## Why it matters

Card frontmatter round-trips through `emit_frontmatter` every time a
field is mutated (`goc status`, `goc decide`, `goc advance`, the
`_mutate_*` helpers). A summary that happens to read `"42"`, a
`worker.who` of `"NO"`, or any free-form field whose value looks like a
YAML int/null/bool is silently rewritten to a non-string scalar on the
next mutation — and downstream code that does `str(card.summary)` then
sees `"42"` vs `"42"` by luck but `"True"` -> `"True"` (Python `str(True)`)
which is a *different string*. It is latent data corruption in the
core persistence path.

## Fix

In `goc/engine.py`, extend the quote-trigger predicate in `_yaml_inline`
so it quotes any value the parser would coerce. Reuse the parser's own
recognizers rather than re-listing them: import (or mirror) `_INT_RE`,
`_NULL_SET`, `_TRUE_SET`, `_FALSE_SET` from `goc/_vendor/yaml_lite.py`
and quote when `s` matches `_INT_RE` or is in the union of the keyword
sets. Optionally include `_DATE_RE` for symmetry (today dates happen to
round-trip as strings, but relying on that is fragile). **Do NOT** quote
genuine Python `int`/`float`/`bool`/`None` values — those are handled by
the earlier `isinstance` branches and must stay bare. Do NOT apply the
fix as part of filing this card.

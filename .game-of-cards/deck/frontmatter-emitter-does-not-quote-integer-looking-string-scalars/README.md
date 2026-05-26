---
title: frontmatter-emitter-does-not-quote-integer-looking-string-scalars
summary: "The frontmatter emitter (`_yaml_inline`) emits integer-looking string scalars (e.g. `\"123\"`, `\"007\"`, `\"-3\"`) bare. The vendored parser then coerces them back to `int`, so the emit->parse round-trip changes the Python type. A card claimed on a numeric branch name gets `worker.where` written as an int and then fails `goc validate` permanently."
status: superseded
stage: null
contribution: medium
created: "2026-05-26T20:41:44Z"
closed_at: "2026-05-26T21:10:22Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero before the fix and non-zero after (no integer-looking string is corrupted)
  - [ ] TDD: `_yaml_inline("123")`, `_yaml_inline("007")`, `_yaml_inline("-3")` each emit a double-quoted scalar, and `yaml_lite.safe_load` reads them back as the original `str`
  - [ ] MECHANICAL: the quote trigger in `_yaml_inline` (goc/engine.py:193-199) covers any scalar the vendored parser would coerce to a non-str type (integer-looking `^-?\d+$`); dates/floats already round-trip as str and need no change
  - [ ] PROCESS: plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check` clean) and `uv run goc validate` clean
superseded_by:
  - frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values
---

# Frontmatter emitter does not quote integer-looking string scalars

## Location

- `goc/engine.py:193-199` — `_yaml_inline` quote-trigger decision.
- `goc/engine.py:168` — `_YAML_RESERVED` (the bare-word set the trigger guards against; omits numbers).
- `goc/_vendor/yaml_lite.py:215-216` — `_parse_scalar` coerces `^-?\d+$` to `int`.
- Trigger path: `goc/engine.py:3312-3318` — `goc status <card> active` builds the
  `worker` mapping via `_yaml_inline(who)` / `_yaml_inline(where)`, where `where`
  comes from the current git branch name.

## What's broken

`_yaml_inline` quotes a string only when it hits one of these triggers
(goc/engine.py:193-199):

```python
if (
    _YAML_NEEDS_QUOTE.search(s)
    or s in _YAML_RESERVED
    or s in _YAML_BLOCK_TOKENS
    or (s and s[0] in _YAML_INDICATOR_FIRST)
    or s != s.strip()
):
```

A plain integer-looking string like `"123"` matches none of them, so it is
emitted **bare**: `where: 123`. The vendored parser then coerces it back to a
different Python type (goc/_vendor/yaml_lite.py:215-216):

```python
if _INT_RE.match(text):   # _INT_RE = re.compile(r"^-?\d+$")
    return int(text)
```

So the emit->parse round-trip is not type-preserving for integer-looking
strings: `"123"` (str) is written, `123` (int) is read back. The emitter and
the parser disagree on the type of the same value.

This is the same *family* as the closed card
[frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values](../frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values/),
but a distinct sub-class: that card quoted values the parser **rejects or
mis-anchors** (indicator-leading, whitespace-padded). It did not cover values
the parser **type-coerces**. Dates (`^\d{4}-\d{2}-\d{2}$`) and floats are
returned as strings by the parser, so they round-trip fine and are out of
scope.

## Empirical evidence

```
CORRUPTED — integer-looking string scalars:
  input='123'          emitted='123'          parsed=123 (int)  round-trips=False
  input='007'          emitted='007'          parsed=7 (int)  round-trips=False
  input='-3'           emitted='-3'           parsed=-3 (int)  round-trips=False

CONTROLS — round-trip correctly (NOT part of this defect):
  input='2026-01-01'   emitted='2026-01-01'   parsed='2026-01-01' (str)  round-trips=True
  input='1.5'          emitted='1.5'          parsed='1.5' (str)  round-trips=True
  input='rodja'        emitted='rodja'        parsed='rodja' (str)  round-trips=True

Realistic worker claim — `where` from a numeric branch name (e.g. issue branch '123'):
  emitted worker value: {who: rodja, where: 123}
  parsed worker: {'who': 'rodja', 'where': 123}
  where is str? False  ->  card would fail validate with "worker: 'where' must be a string": True

BUG PRESENT (integer-looking strings do not round-trip): True
```

## Why it matters

The validator requires `worker.who` and `worker.where` to be strings
(goc/engine.py:1078-1081):

```python
elif not isinstance(worker.get("who"), str) or not worker["who"]:
    errors.append(f"{t.title}: worker: 'who' must be a non-empty string")
if "where" in worker and not isinstance(worker.get("where"), str):
    errors.append(f"{t.title}: worker: 'where' must be a string")
```

Branches named after issue/PR numbers (`123`) or other all-digit branch names
are common. When `goc status <card> active` auto-populates `worker.where` from
such a branch, the value is written bare, read back as an `int`, and the card
then **fails `goc validate` permanently** until someone hand-edits the
frontmatter to add quotes. A zero-padded machine id (`007`) is additionally
silently mangled to `7`, corrupting `goc --worker` matching even where the
validator would otherwise pass. The corruption is silent at write time — it
only surfaces on the next load.

## Fix

Extend the quote trigger in `_yaml_inline` so any scalar that the vendored
parser would coerce to a non-`str` type is quoted. The minimal change is to add
an integer-shape check mirroring the parser's `_INT_RE`:

```python
or re.fullmatch(r"-?\d+", s)   # parser would coerce this to int
```

Keep it aligned with the parser's coercion set: today only `^-?\d+$` coerces
(dates and floats already return `str`), so an int-shape guard is sufficient.
If `_parse_scalar` later grows a float/other-type branch, the trigger must grow
with it — note this coupling so the two stay in sync. Do NOT apply the fix in
this card; this is the audit filing.

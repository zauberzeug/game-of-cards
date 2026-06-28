---
title: yaml-lite-coerces-leading-zero-scalars-to-int-corrupting-string-values
summary: "The vendored YAML parser's integer regex `_INT_RE = ^-?\\d+$` over-matches leading-zero decimal scalars, so a bare frontmatter value like `008` parses to the int `8` and `0123` to `123` — values that are strings under both YAML 1.2 and PyYAML's 1.1 resolver. A hand-edited `worker: 008` becomes int `8`, which `goc validate` then rejects as 'must be a string' and `--worker` filtering silently drops. Fix: tighten the regex to the canonical decimal-integer form."
status: done
stage: null
contribution: low
created: "2026-06-28T02:10:26Z"
closed_at: "2026-06-28T02:14:36Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (leading-zero scalars `008`/`0123`/`00` parse as strings, not ints)
  - [x] TDD: canonical integers still parse as ints (`0`, `42`, `-5`) and non-leading-zero round-trips are unchanged
  - [x] MECHANICAL: `_INT_RE` in `goc/_vendor/yaml_lite.py` tightened to the canonical decimal-integer form
  - [x] PROCESS: a regression test lands in `tests/` and `uv run python -m unittest discover -s tests` passes
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# yaml-lite parses leading-zero scalars as ints, corrupting string values

## Location

`goc/_vendor/yaml_lite.py:35` (the regex) and `:338-339` (the coercion):

```python
_INT_RE = re.compile(r"^-?\d+$")
...
    if _INT_RE.match(text):
        return int(text)
```

## What's broken

`_INT_RE = ^-?\d+$` matches any run of digits, including leading-zero
decimal strings. `_parse_scalar` then calls Python's `int()`, which
happily strips leading zeros: `int("008") == 8`, `int("0123") == 123`,
`int("00") == 0`. So a bare scalar that is **not** a valid YAML integer
is silently coerced to an int with a different textual value.

Under both relevant specifications these tokens are strings, not ints:

- **YAML 1.2** — the canonical integer form is `0 | -?[1-9][0-9]*`.
  Any other leading-zero run (`008`, `0123`, `00`, `007`) is a plain
  string.
- **PyYAML's default (YAML 1.1) resolver** — `008`/`009` match neither
  the octal pattern (`8`/`9` are not octal digits) nor the decimal
  pattern (which forbids a leading zero), so PyYAML returns the string
  `"008"`. yaml_lite's own bool set (`yes`/`no`/`Yes`/...) shows it
  follows PyYAML's 1.1 resolver semantics, so PyYAML is the relevant
  compatibility baseline — and yaml_lite diverges from it here.

`008` is therefore unambiguously wrong under *every* interpretation:
YAML 1.2 says string, PyYAML says string, yaml_lite says int `8`. (The
only borderline token is `007`, which PyYAML reads as octal `7`;
yaml_lite never supported octal/hex/binary and the docstring only
claims plain "integer", so collapsing `007` to the string `"007"` is
the data-preserving, surprise-free choice and the emitter quotes such
values on write, keeping round-trips stable.)

## Empirical evidence (post-fix)

reproduce.py exits 0 after the fix; before the fix the first four rows
read `[BUG]` with the leading zeros stripped (`008`→`8`, `0123`→`123`,
`00`→`0`) and `worker: 008` resolved to `''`:

```
$ uv run python .game-of-cards/deck/yaml-lite-coerces-leading-zero-scalars-to-int-corrupting-string-values/reproduce.py
'008'  -> '008'    (type str) EXPECTED '008' (str) ok
'009'  -> '009'    (type str) EXPECTED '009' (str) ok
'0123' -> '0123'   (type str) EXPECTED '0123' (str) ok
'00'   -> '00'     (type str) EXPECTED '00' (str) ok
'0'    -> 0        (type int) EXPECTED 0 (int) ok
'42'   -> 42       (type int) EXPECTED 42 (int) ok
'-5'   -> -5       (type int) EXPECTED -5 (int) ok
worker:008 -> _worker_who returns '008' ok
```

## Why it matters

The parser is the read half of the frontmatter round-trip; every card
load goes through `safe_load`. The reachability path is **hand-edited
frontmatter** (the documented contract — humans edit frontmatter by
hand per AGENTS.md's "YAML format for list fields" guidance). A
human-authored `worker: 008` (a zero-padded agent/machine id, a
plausible free-form `worker` value) parses to the int `8`. Two shipping
consumers then misbehave:

- `_worker_who` (`goc/engine.py:813`) returns `""` for any non-`str`,
  non-`dict` value, so `goc --worker 008` substring-matches against the
  empty string and the card vanishes from its own worker queue.
- `goc validate` (`goc/engine.py:1632`) rejects the coerced int with
  `worker: must be a string or mapping with 'who'` — a confusing error
  for a value the user wrote as a perfectly ordinary string.

The class is broader than `worker`: any bare digit-with-leading-zero
value a human types into any string field is silently retyped, and
downstream string operations on it (`.strip()`, `.lower()`, `in`) then
hit an int. The emitter already quotes integer-looking strings on write
(see closed `frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values`),
so goc never *produces* this shape — but it must *read* hand-authored
input faithfully, and right now it doesn't.

## Fix (applied)

`_INT_RE` was tightened to the canonical decimal-integer form so
leading-zero runs fall through to the string branch:

```python
_INT_RE = re.compile(r"^-?(0|[1-9][0-9]*)$")
```

`0`, `42`, `-5` keep parsing as ints; `00`, `007`, `008`, `0123` now
parse as their literal strings. Single-site change in
`goc/_vendor/yaml_lite.py:35`; regression test added to
`tests/test_yaml_lite.py` (`ScalarTest.test_leading_zero_scalar_stays_string`).
Plugin mirrors (`claude-plugin`, `codex-plugin`, `openclaw-plugin`)
re-synced from the source.

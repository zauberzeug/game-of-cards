---
title: frontmatter-emitter-does-not-quote-empty-string-scalar-that-parses-as-null
summary: "The frontmatter emitter writes an empty-string field as a bare `key: ` line, which the vendored parser reads back as `None` — a silent str -> None mutation on every card rewrite. `_parser_coerces_scalar` omits the parser's `not text` (empty -> None) branch, so the quote-trigger and parser coercion drift, exactly the failure its docstring claims it prevents. Third instance of the emitter-quote-class family."
status: done
stage: null
contribution: medium
created: "2026-05-26T21:44:33Z"
closed_at: 2026-05-26T21:48:20Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (an empty-string field round-trips back to `""`, not `None`).
  - [x] MECHANICAL: `_parser_coerces_scalar` (or the emitter quote-trigger) recognizes the empty string as parser-coerced, so `_yaml_inline("")` returns `'""'`.
  - [x] EMPIRICAL: `uv run goc validate` stays clean and the existing emitter sibling reproducers still pass.
  - [x] PROCESS: log.md records whether the fix lands in `_parser_coerces_scalar` or as a standalone empty-string guard, and notes this is the 3rd family instance (a 4th warrants the round-trip-by-construction meta-fix).
worker: {who: "claude[bot]", where: main}
---

# Frontmatter emitter does not quote the empty string, so it parses back as null

## Location

- `goc/engine.py:209-220` — `_yaml_inline`: for `value == ""`, `s = str("")` is `""`; no quote guard fires, so it returns the bare empty string.
- `goc/engine.py:177-192` — `_parser_coerces_scalar`: checks `_NULL_SET / _TRUE_SET / _FALSE_SET / _INT_RE` but NOT the parser's empty-string branch.
- `goc/_vendor/yaml_lite.py:219-222` — `_parse_scalar`: `if not text or text in _NULL_SET: return None`. The leading `not text` clause is the empty-string -> None coercion the emitter guard omits.

## What's broken

The emitter's quote-trigger is supposed to mirror the parser's coercion
recognizers exactly. Its docstring states this as an invariant:

> Derived by reference from the parser's own recognizers
> (`yaml._INT_RE`, `yaml._NULL_SET`, `yaml._TRUE_SET`, `yaml._FALSE_SET`)
> so the emitter's quote-trigger and the parser's coercion cannot drift.

But the parser coerces in a branch the guard never consulted —
`if not text` at `yaml_lite.py:221` turns the empty string into `None`
before `_NULL_SET` is even checked. `_NULL_SET` is
`{"null", "Null", "NULL", "~"}` and does not contain `""`, so
`_parser_coerces_scalar("")` returns `False`, and the emitter writes a
bare `summary: ` line. On the next load that field is `None`.

This is a live, in-tree demonstration: `goc new` scaffolded *this very
card* with a bare `summary: ` line (before it was hand-quoted), which
`parse_frontmatter` would read as `summary: None`.

## Empirical evidence

```
emitted frontmatter:
---
title: t
summary: 
---

original summary:      ''
round-tripped summary: None

_parser_coerces_scalar(''): False  (emitter believes '' is safe to emit bare)
round-trip preserved:       False

FAIL: empty string round-tripped to a different value (None); the emitter must quote it as "".
```

## Why it matters

Any card whose string field is empty (an unset `summary`, a stage label,
a worker `who`) silently mutates from `""` to `None` the first time the
card is rewritten by `goc status`, `goc advance`, `goc done`, etc. The
emitter then renders `None` as `null`, so the empty string becomes the
literal token `null` — a semantic change the author never made. Downstream
code that distinguishes "empty string" from "absent/null" (e.g. truthiness
checks, schema-required-field validation) sees the wrong type.

This is the 3rd instance of the emitter-quote-class family:
- [frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values](../frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values/)
- [frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values](../frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values/)

Each instance is "the emitter forgot one value class the parser coerces."
The structural fix (a 4th instance should trigger it) is to derive the
quote decision *by construction* — emit, re-parse, and quote iff the
re-parsed value differs from the input — instead of re-enumerating the
parser's recognizers by hand in `_parser_coerces_scalar`.

## Fix (applied)

`_parser_coerces_scalar` (`goc/engine.py`) now leads its disjunction
with `s == ""`, mirroring the parser's `if not text` empty-string
branch (`yaml_lite.py:221`). `_yaml_inline("")` now falls into the
quote branch and emits `""`, which the parser reads back as the empty
string instead of `None`. The docstring's "cannot drift" invariant is
restored: the guard now consults every parser coercion branch
(empty-string + `_NULL_SET` + `_TRUE_SET` + `_FALSE_SET` + `_INT_RE`).
`reproduce.py` exits 0 (round-trip `'' -> '' `).

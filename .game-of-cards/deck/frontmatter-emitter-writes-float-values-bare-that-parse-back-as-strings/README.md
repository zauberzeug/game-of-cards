---
title: frontmatter-emitter-writes-float-values-bare-that-parse-back-as-strings
summary: "UNVERIFIED / latent. `_yaml_inline` emits `float` values bare via `str(value)` (`engine.py:209-210`), but the vendored parser's scalar recognizers have an int regex and no float regex (`yaml_lite.py:227`), so a bare `3.14` falls through to `return text` and reads back as the string '3.14'. No current schema field is a float, so this is unreachable today — but the emitter explicitly advertises float support, leaving a latent emit->parse type-loss gap of the same class as the closed int/null/bool quoting fixes."
status: done
stage: null
contribution: low
created: "2026-05-26T21:57:44Z"
closed_at: 2026-05-26T22:13:28Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] PROCESS: decide whether to (a) drop float handling from `_yaml_inline` (no schema field is a float — emitter should not advertise unsupported types) or (b) add a float recognizer to the parser to close the round-trip. Record the call in log.md. → chose (a): refuse floats at the emit boundary (see log.md).
  - [x] TDD: reproduce.py exits zero under the chosen approach — either floats round-trip as floats, or the emitter refuses/quotes them so no silent string-coercion occurs.
  - [x] TDD: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# Frontmatter emitter writes float values bare that parse back as strings

## The gap (confirmed, latent — no live schema field exercised it)

Emit side, `goc/engine.py`:

```python
if isinstance(value, (int, float)):
    return str(value)
```

Parse side, `goc/_vendor/yaml_lite.py` (the only numeric recognizer):

```python
if _INT_RE.match(text):   # _INT_RE = re.compile(r"^-?\d+$") — integers only
    return int(text)
```

A genuine Python `float` (e.g. `3.14`) was emitted bare as `3.14`, but the
parser has no float regex, so `_parse_scalar` fell through to `return text`
and yielded the **string** `"3.14"`. This is the same type-loss class the team
closed for int/null/bool *string* values
([frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values](../frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values/)),
but in the reverse direction — a real float type the parser never coerces — so
`_parser_coerces_scalar` did not catch it either.

## Fix (applied — option a: refuse at the emit boundary)

No card frontmatter field is a float — contribution/value scores are computed
at render time and never stored — so a float never legitimately reaches
`_yaml_inline`. Rather than add a float recognizer to the parser for a type the
schema never uses (option b, speculative surface + float edge cases like
`inf`/`nan`/`1e20`), the emitter now **refuses floats** at the serialization
boundary:

```python
if isinstance(value, int):
    return str(value)
if isinstance(value, float):
    raise FrontmatterError(
        f"float frontmatter values are not supported (got {value!r}); "
        "store the value as a string or int."
    )
```

This fails loud instead of silently coercing float→string, and is drift-proof:
there is no second float truth-set to keep in sync with the parser (the
recurring root cause behind the int/null/bool sibling cards). A bare drop alone
would not have sufficed — a float falling through to `str(value)` is not caught
by the quote-triggers and would still emit bare and read back as a string. See
log.md for the full PROCESS decision.

## Verification

`reproduce.py` exits 0: emitting a float raises `FrontmatterError` (refused, no
silent coercion), while a genuine `int` still round-trips bare as `int` and a
float-looking *string* (`"3.14"`) still round-trips as a string.

Surfaced by a general-purpose hunter agent during an audit-deck pass.

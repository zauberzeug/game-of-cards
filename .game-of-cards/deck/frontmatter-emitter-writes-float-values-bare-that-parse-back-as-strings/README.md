---
title: frontmatter-emitter-writes-float-values-bare-that-parse-back-as-strings
summary: "UNVERIFIED / latent. `_yaml_inline` emits `float` values bare via `str(value)` (`engine.py:209-210`), but the vendored parser's scalar recognizers have an int regex and no float regex (`yaml_lite.py:227`), so a bare `3.14` falls through to `return text` and reads back as the string '3.14'. No current schema field is a float, so this is unreachable today — but the emitter explicitly advertises float support, leaving a latent emit->parse type-loss gap of the same class as the closed int/null/bool quoting fixes."
status: open
stage: null
contribution: low
created: "2026-05-26T21:57:44Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] PROCESS: decide whether to (a) drop float handling from `_yaml_inline` (no schema field is a float — emitter should not advertise unsupported types) or (b) add a float recognizer to the parser to close the round-trip. Record the call in log.md.
  - [ ] TDD: reproduce.py exits zero under the chosen approach — either floats round-trip as floats, or the emitter refuses/quotes them so no silent string-coercion occurs.
  - [ ] TDD: `uv run goc validate` passes.
---

# Frontmatter emitter writes float values bare that parse back as strings

## Hypothesis (unverified — latent, no live schema field exercises it)

Emit side, `goc/engine.py:209-210`:

```python
if isinstance(value, (int, float)):
    return str(value)
```

Parse side, `goc/_vendor/yaml_lite.py:227` (the only numeric recognizer):

```python
if _INT_RE.match(text):   # _INT_RE = re.compile(r"^-?\d+$") — integers only
    return int(text)
```

A genuine Python `float` (e.g. `3.14`) is emitted bare as `3.14`, but the
parser has no float regex, so `_parse_scalar` falls through to `return text`
and yields the **string** `"3.14"`. This is the same type-loss class the team
closed for int/null/bool *string* values
([frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values](../frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values/)),
but in the reverse direction — a real float type the parser never coerces — so
`_parser_coerces_scalar` (`engine.py:177`) does not catch it either.

## Why deferred (and why unverified rather than filed)

No card frontmatter field is a float today — contribution/value scores are
computed at render time and never stored. So the path is currently unreachable
through normal goc operation, making it a latent API-contract gap rather than a
live data-loss bug. Parked unverified pending the `PROCESS` decision in the DoD:
the cleaner resolution may be to stop advertising float support in the emitter
rather than to add a float recognizer for a type the schema never uses.

## Falsification recipe

```python
from goc.engine import emit_frontmatter, parse_frontmatter
text = emit_frontmatter({"title": "x", "k": 3.14}) + "\nbody\n"
back, _ = parse_frontmatter(text)
# Prediction: type(back["k"]) is str and back["k"] == "3.14"
assert type(back["k"]) is float, (type(back["k"]), back["k"])
```

Surfaced by a general-purpose hunter agent during an audit-deck pass.

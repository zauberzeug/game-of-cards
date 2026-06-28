---
title: frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror
summary: "When a card's README.md has both `---` delimiters and the YAML between them parses cleanly to a non-mapping value (a block list, or some bare scalars), `parse_frontmatter`'s `or {}` guard passes the non-dict through and `load_card` then calls `fm.get(...)`, raising a raw `AttributeError` with a Python traceback instead of the `FrontmatterError` the loader contract promises. Same point-away-from-the-problem failure the unterminated-frontmatter card already eliminated, for an input shape that fix never anticipated."
status: done
stage: null
contribution: medium
created: "2026-05-27T13:49:20Z"
closed_at: "2026-05-27T13:54:52Z"
human_gate: none
advances:
  - unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — every non-mapping frontmatter shape (top-level list, bare scalar, int) is handled coherently instead of raising a raw AttributeError.
  - [x] TDD: `parse_frontmatter` raises `FrontmatterError` (not AttributeError) when the YAML between `---` delimiters parses to a non-mapping type; the message names the actual problem (frontmatter is not a mapping).
  - [x] TDD: a regression test in `tests/` covers list/scalar top-level frontmatter and asserts `FrontmatterError`.
  - [x] EMPIRICAL: `uv run goc validate` on a deck containing such a card reports a coherent per-card error (not a bare traceback).
worker: {who: "claude[bot]", where: main}
---

# frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror

## Location

`goc/engine.py:161` (`data = yaml.safe_load(m.group(1)) or {}`), surfacing
at `goc/engine.py:589` (`fm.get("definition_of_done", "")` in `load_card`).

## What's broken

`parse_frontmatter` is contracted to return `tuple[dict, str]` and every
caller assumes the first element is a dict. The guard only normalizes the
empty/None case:

```python
try:
    data = yaml.safe_load(m.group(1)) or {}
except ValueError as exc:
    raise FrontmatterError(
        f"YAML parse error inside frontmatter: {exc}"
    ) from exc
return data, m.group(2)
```

When the YAML between the `---` delimiters is *valid* but parses to a
**non-mapping** — a block list, or certain bare scalars — `data` becomes
that list/scalar. `or {}` does not catch it (a non-empty list is truthy).
`load_card` then runs:

```python
fm, body = parse_frontmatter(readme.read_text())
if not fm:
    return None
dod_field = fm.get("definition_of_done", "")   # <-- AttributeError on a list
```

A non-empty list passes `if not fm`, so control reaches `fm.get(...)` and
raises `AttributeError: 'list' object has no attribute 'get'` — a raw
traceback with no card name and no diagnostic.

This is the same failure class the closed card
[malformed-frontmatter-yields-inconsistent-misleading-errors-across-commands](../malformed-frontmatter-yields-inconsistent-misleading-errors-across-commands/)
fixed for the *missing-closing-delimiter* case: that card introduced
`FrontmatterError` precisely so malformed frontmatter yields a coherent,
card-naming error instead of a misleading one. It only handled the
unterminated case (no closing `---`); it never anticipated well-formed
frontmatter that parses to the wrong *type*. The `or {}` guard is the gap.

## Empirical evidence

Pre-fix the list case crashed; post-fix all shapes are coherent:

```
[PASS] top-level list       -> FrontmatterError: frontmatter is not a mapping: ... parsed to a list, expected key/value pairs
[PASS] bare scalar string   -> returned None
[PASS] top-level int        -> returned None

OK: all non-mapping frontmatter shapes handled coherently
```

(The bare-scalar / int cases are coerced by the vendored `yaml_lite`
parser to `{}` — `safe_load("justastring\n")` returns `{}`, not the
scalar — so `if not fm` treats them as non-card and returns `None`.
Only the block list parses to a real non-mapping value, which is the
case the `isinstance` guard now routes through `FrontmatterError`.)

## Why it matters

A card README authored in one shot can elide structure — e.g. a body that
accidentally starts the frontmatter with a `-` list item. The whole deck
then becomes un-loadable: `goc validate`, `goc` (queue), and `goc --board`
all crash with a Python traceback that names no card, sending the reader
hunting through every README by hand. The earlier card invested in making
this exact situation legible; this input shape slips past that work.

## Fix

`parse_frontmatter` (`goc/engine.py`) now rejects a non-mapping result
after `safe_load`:

```python
data = yaml.safe_load(m.group(1))
if data is None:
    data = {}
elif not isinstance(data, dict):
    raise FrontmatterError(
        "frontmatter is not a mapping: the YAML between the '---' "
        f"delimiters parsed to a {type(data).__name__}, expected key/value pairs"
    )
return data, m.group(2)
```

This routes the non-mapping shape through the same `FrontmatterError`
channel `load_card_or_exit` already turns into a per-card diagnostic, so
`goc validate` / `goc done` / `goc show` report a coherent story instead
of a bare traceback. Replacing the old `or {}` with the explicit
`None`-vs-non-dict split also stops silently swallowing the empty-string
edge while preserving the empty-frontmatter `{}` contract.

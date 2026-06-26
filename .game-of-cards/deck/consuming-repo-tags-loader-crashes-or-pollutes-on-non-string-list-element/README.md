---
title: consuming-repo-tags-loader-crashes-or-pollutes-on-non-string-list-element
summary: "`_load_consuming_repo_tags()` (engine.py:620-627) guards the *shape* of a `canonical_tags:` block (list vs non-list) but never type-checks its *elements*. A non-string element crashes the entire CLI on unhashable values (`TypeError: unhashable type` via `set.update`) or silently pollutes the canonical-tag set on hashable ones (ints, bools). Because `load_schema()` calls this loader, the crash takes down every `goc` command, not just `validate`."
status: done
stage: null
contribution: medium
created: "2026-06-26T01:48:08Z"
closed_at: "2026-06-26T01:52:50Z"
human_gate: none
advances:
  - bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — `_load_consuming_repo_tags()` against a `canonical-tags.md` whose `canonical_tags:` list contains an unhashable element (nested list) returns the valid string tags rather than raising `TypeError`, and a list with hashable non-string elements (int, bool) drops them rather than adding them to the set.
  - [x] MECHANICAL: `_load_consuming_repo_tags()` (engine.py:620-627) filters list elements to `str` before `out.update`, matching the established non-string-element guard family.
  - [x] TDD: regression test in `tests/test_consuming_repo_tags_loader.py` covers both the unhashable-element crash case and the hashable-non-string pollution case (extending the existing shape-guard tests).
  - [x] MECHANICAL: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; `pre-commit run --all-files` clean (plugin mirrors auto-sync).
worker: {who: "claude[bot]", where: main}
---

# `_load_consuming_repo_tags` crashes or pollutes the tag set on a non-string list element

## Location

`goc/engine.py:620-627` — `_load_consuming_repo_tags()`:

```python
out: set[str] = set()
for match in _FENCED_YAML.finditer(extension_file.read_text()):
    block = yaml.safe_load(match.group(1)) or {}
    value = block.get("canonical_tags") or []
    if not isinstance(value, list):
        continue
    out.update(value)
return out
```

## What's broken

The closed card
[canonical-tags-loader-iterates-bare-string-scalar-character-by-character](../canonical-tags-loader-iterates-bare-string-scalar-character-by-character/)
added the `isinstance(value, list)` *shape* guard on line 624. That
guard rejects a bare-string scalar (`canonical_tags: my-tag`), but it
only checks the *container*. Once `value` is a list, every element is
passed straight to `set.update()` with **no per-element type check** —
unlike every other list-field consumer in the engine, which guards
elements (the closed/open `*-non-string-element-*` family).

Two distinct failure modes follow from a user typo in the
user-authored `.game-of-cards/canonical-tags.md`:

1. **Hard crash (unhashable element).** A nested list or mapping under
   `canonical_tags:` makes `set.update([...])` raise
   `TypeError: unhashable type: 'list'`. The exception is unhandled.

   ```yaml
   canonical_tags:
     - good-tag
     - [nested, list]
   ```

2. **Silent pollution (hashable non-string).** An int or bool element
   is added verbatim to the set:

   ```yaml
   canonical_tags:
     - good-tag
     - 123
     - true
   ```

   yields `{'good-tag', 123, True}`. The non-string members can never
   satisfy a string-tag comparison (`"123" not in canonical_tags`
   stays true), so validation silently misbehaves.

## Empirical evidence

Before the fix, `reproduce.py` printed (defect present):

```
unhashable element: CRASH: TypeError unhashable type: 'list'
hashable non-string elements: RESULT: {'good-tag', True, 123}
FAIL: defect present
```

After the element-filter guard, it exits 0:

```
$ uv run python deck/consuming-repo-tags-loader-crashes-or-pollutes-on-non-string-list-element/reproduce.py
unhashable element: RESULT: {'good-tag'}
hashable non-string elements: RESULT: {'good-tag'}
PASS: non-string list elements are filtered, not crashed/added
```

## Why it matters

`load_schema()` calls `_load_consuming_repo_tags()` on every run, and
nearly every `goc` verb calls `load_schema()`. So failure mode 1 does
not merely break `goc validate` — a single typo in a consuming repo's
`canonical-tags.md` (e.g. an accidentally-indented nested item) crashes
**every** `goc` command with an unhandled traceback, with no hint that
the schema-extension file is the culprit.

Reachability: the input is user-authored project state. The
`canonical-tags.md` file is explicitly documented as the place
consuming repos extend the tag enum (see `_UNKNOWN_TAG_REMEDY` and the
loader docstring), and YAML's whitespace sensitivity makes a stray
nested item or unquoted numeric tag an easy hand-edit mistake.

This is the third instance of the "list-field consumer does not
type-check elements" family on the *deck-extension* surface, alongside
[goc-validate-crashes-with-typeerror-on-non-string-element-in-tags-list](../goc-validate-crashes-with-typeerror-on-non-string-element-in-tags-list/)
and
[goc-validate-crashes-with-typeerror-on-non-string-element-in-relationship-list](../goc-validate-crashes-with-typeerror-on-non-string-element-in-relationship-list/)
(both on a card's frontmatter). It is higher-severity than those two:
the others break one verb, this one breaks the whole CLI.

## Fix

Filter list elements to strings in the comprehension, mirroring the
established guard idiom:

```python
out.update(t for t in value if isinstance(t, str))
```

This drops both unhashable and hashable-non-string elements while
preserving valid string tags — no crash, no pollution.

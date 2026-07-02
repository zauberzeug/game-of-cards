---
title: canonical-tags-loader-crashes-on-yaml-block-that-is-not-a-mapping
summary: "`_load_consuming_repo_tags` assumes every fenced YAML block in canonical-tags.md parses to a mapping and calls `block.get(\"canonical_tags\")` unconditionally. A block that is a valid YAML list crashes with AttributeError. Because load_schema() runs at module import, every goc command then dies with a raw traceback."
status: done
stage: null
contribution: medium
created: "2026-07-02T01:35:17Z"
closed_at: "2026-07-02T01:39:39Z"
human_gate: none
advances:
  - bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (loader returns set() for a list-shaped fenced block instead of raising AttributeError)
  - [x] TDD: a fenced YAML block that parses to a non-mapping (list, scalar, int) is skipped, not `.get()`-ed
  - [x] TDD: well-formed `canonical_tags:` mapping blocks still merge as before (no regression)
  - [x] MECHANICAL: the `isinstance(block, dict)` guard lands in `_load_consuming_repo_tags` at engine.py
  - [x] PROCESS: `uv run goc validate` passes and the regression suite is green
worker: {who: "claude[bot]", where: main}
---

# canonical-tags-loader-crashes-on-yaml-block-that-is-not-a-mapping

## Location

`goc/engine.py:645-647`, function `_load_consuming_repo_tags`.

## What's broken

The loader walks every fenced ` ```yaml ` block in
`.game-of-cards/canonical-tags.md` and calls `.get(...)` on the parsed
result without checking that it is a mapping:

```python
for match in _FENCED_YAML.finditer(extension_file.read_text()):
    block = yaml.safe_load(match.group(1)) or {}
    value = block.get("canonical_tags") or []      # assumes block is a dict
    if not isinstance(value, list):
        continue
    out.update(t for t in value if isinstance(t, str))
```

There are guards on `value` (the mapping's value must be a list) and on
the list *elements* (each must be a `str`) — added by two prior sibling
cards — but **nothing guards `block` itself**. `_FENCED_YAML` matches
*every* ` ```yaml ` block in the file, and a Markdown author can easily
write a block that parses to something other than a mapping.

The docstring shows the intended shape (a `canonical_tags:` mapping),
but a user who documents their tags as a bare list —

````markdown
```yaml
- frontend
- backend
```
````

— produces `block == ["frontend", "backend"]`, a `list`. `list.get`
does not exist, so `block.get("canonical_tags")` raises
`AttributeError: 'list' object has no attribute 'get'`. A bare-scalar
block (` ```yaml\njusttext\n``` `) instead raises `ParseError` inside
`yaml.safe_load` — a separate malformed-input class not addressed here.

## Empirical evidence

Before the fix, `reproduce.py` crashed:

```
list-shaped fenced yaml block:
  CRASH: AttributeError 'list' object has no attribute 'get'
expected: set()  (block is not a mapping -> skip it)
```

After the `isinstance(block, dict)` guard landed:

```
$ uv run python .game-of-cards/deck/canonical-tags-loader-crashes-on-yaml-block-that-is-not-a-mapping/reproduce.py
list-shaped fenced yaml block:
  result: set()
  OK: non-mapping block skipped, returned set()
```

## Why it matters

`load_schema()` merges these tags (`engine.py:599`), and
`_ENUM_SCHEMA = load_schema()` runs at **module import** (`engine.py:2225`).
So the crash fires before argparse even sees the command — `goc`,
`goc validate`, `goc new`, `goc status`, *every* verb dies with a raw
traceback rather than a clean diagnostic, and the deck is unusable until
the file is hand-edited. `canonical-tags.md` is one of the six
user-owned content stubs `goc install` scaffolds, so a consuming repo's
maintainer editing it by hand is the reachability path: they read the
` ```yaml ` fences elsewhere in their docs, copy the shape, and write a
list instead of a `canonical_tags:` mapping.

This is the same defensive-loader family as the two closed siblings
[canonical-tags-loader-iterates-bare-string-scalar-character-by-character](../)
(guarded the value under the key) and
[consuming-repo-tags-loader-crashes-or-pollutes-on-non-string-list-element](../)
(guarded the list elements) — but orthogonal to both: it guards the
block's own type. Third instance of the family; under the four-instance
meta-fix threshold, so it lands as its own guard.

## Fix

Add a mapping-type guard on `block` immediately after parsing, so a
non-mapping fenced block is skipped like any other malformed shape:

```python
block = yaml.safe_load(match.group(1)) or {}
if not isinstance(block, dict):
    continue
value = block.get("canonical_tags") or []
```

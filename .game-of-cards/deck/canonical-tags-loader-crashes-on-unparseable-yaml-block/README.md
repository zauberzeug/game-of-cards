---
title: canonical-tags-loader-crashes-on-unparseable-yaml-block
status: done
stage: null
contribution: high
created: "2026-07-03T01:05:48Z"
closed_at: "2026-07-03T01:11:32Z"
human_gate: none
advances:
  - unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes
advanced_by: []
tags: [bug, infra, api-contract]
summary: |
  `_load_consuming_repo_tags` calls `yaml.safe_load` on every fenced YAML
  block in `canonical-tags.md` without a try/except, so an unparseable
  block (folded `>` scalar, anchor, tab indent) raises `ParseError` out of
  `load_schema()` at import time and crashes every goc command. The sibling
  loaders (`load_deck_config`, `parse_frontmatter`, `_resolve_deck_root`)
  already guard this; this one is the lone gap.
definition_of_done: |
  - [x] TDD: a regression test in tests/test_consuming_repo_tags_loader.py drives a canonical-tags.md whose fenced block uses an unsupported YAML feature (folded `>` scalar) and asserts `_load_consuming_repo_tags()` returns a set (no raised ParseError)
  - [x] TDD: the same test confirms a well-formed sibling block in the same file still contributes its tags (a parse error in one block does not drop the others)
  - [x] TDD: reproduce.py exits zero after the fix (import + load succeeds; malformed block skipped silently)
  - [x] MECHANICAL: the `yaml.safe_load(match.group(1))` at goc/engine.py:646 is wrapped in try/except that skips the block on ParseError, mirroring load_deck_config's guard
  - [x] PROCESS: log.md records the fix and the sibling-guard family it completes
worker: {who: "claude[bot]", where: main}
---

# canonical-tags-loader-crashes-on-unparseable-yaml-block

## Location

`goc/engine.py:646`, inside `_load_consuming_repo_tags`.

## What's broken

`_load_consuming_repo_tags` iterates every fenced YAML block in the
user-owned `canonical-tags.md` and parses each one:

```python
for match in _FENCED_YAML.finditer(extension_file.read_text()):
    block = yaml.safe_load(match.group(1)) or {}
    # Guard the block itself, not just its value ...
    if not isinstance(block, dict):
        continue
```

The recent hardening added an `isinstance(block, dict)` guard for the
*non-mapping* shape, and an element filter for non-string tags — but the
`yaml.safe_load(...)` call itself is **not wrapped in try/except**. The
vendored parser (`goc/_vendor/yaml_lite`) is a strict subset of YAML and
raises `ParseError` (a `ValueError` subclass) on features PyYAML accepts:
folded scalars (`>`), anchors/aliases/tags (`&`/`*`/`!`), and tab
indentation.

`_FENCED_YAML` matches **every** ` ```yaml ` block in the file, not only
the intended `canonical_tags:` one — so any illustrative or unrelated
YAML example a user writes into their tags doc can trip the parser.

The sibling loader `load_deck_config` guards exactly this at
`goc/engine.py:4660-4663`, and its own comment claims parity:

```python
data = yaml.safe_load(path.read_text())
except Exception:
    return {}
...
# Mirrors the isinstance guards in `_resolve_deck_root` and
# `_load_consuming_repo_tags`.
```

But `_load_consuming_repo_tags` never got the try/except — only the
isinstance guard. `parse_frontmatter` (engine.py:169) and
`_resolve_deck_root` (engine.py:88) both wrap their `safe_load` too. This
is the lone unguarded user-facing `safe_load` callsite.

## Why it matters — reachability

`_ENUM_SCHEMA = load_schema()` runs at **module import time**
(`goc/engine.py:2239`), and `load_schema()` calls `_load_consuming_repo_tags()`
unguarded (`engine.py:599`). So a `ParseError` propagates straight out of
`import goc.engine` — breaking *every* subcommand, including
`goc --help` and `goc validate`, the very commands a user would run to
diagnose the problem.

`canonical-tags.md` is a **user-owned content stub** (hand-authored
markdown, never overwritten by `goc upgrade`). A user documenting their
project tags who pastes a YAML example using a folded scalar, an anchor,
or tab-indents a block produces the offending input directly. This is the
same total blast radius as the closed sibling
[canonical-tags-loader-crashes-on-yaml-block-that-is-not-a-mapping](../canonical-tags-loader-crashes-on-yaml-block-that-is-not-a-mapping/).

## Empirical evidence

```
$ python3 -c "import goc.engine"   # cwd has .game-of-cards/canonical-tags.md
  File ".../goc/_vendor/yaml_lite.py", line 311, in _resolve_value
    raise ParseError(f"line {self._pos + 1}: folded scalars (>) not supported")
goc._vendor.yaml_lite.ParseError: line 4: folded scalars (>) not supported
```

The triggering `canonical-tags.md`:

```yaml
canonical_tags:
  - my-tag
description: >
  folded example text
```

(A tab-indented block or one using `&anchor` / `!tag` triggers the same
crash.) See `reproduce.py`.

## Fix

Wrap the `safe_load` in a try/except that skips the block, mirroring
`load_deck_config`:

```python
for match in _FENCED_YAML.finditer(extension_file.read_text()):
    try:
        block = yaml.safe_load(match.group(1)) or {}
    except Exception:
        continue
    if not isinstance(block, dict):
        continue
    ...
```

A malformed block is dropped silently while any well-formed sibling block
still contributes its tags.

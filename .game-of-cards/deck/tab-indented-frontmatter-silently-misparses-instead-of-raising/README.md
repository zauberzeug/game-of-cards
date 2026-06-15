---
title: tab-indented-frontmatter-silently-misparses-instead-of-raising
summary: "The vendored YAML parser's docstring lists `Tabs as indentation` under `Unsupported (raises ParseError)`, but `_indent()` counts a tab as one indentation character with no tab guard. Tab-indented frontmatter parses silently — and a tab+space-indented key is promoted to a top-level sibling, corrupting the document structure instead of failing loud."
status: active
stage: null
contribution: low
created: "2026-06-15T05:47:20Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — tab-indented structural lines now raise ParseError instead of silently parsing
  - [ ] TDD: a regression test in tests/ asserts ParseError on tab-indented mapping/sequence/mixed-indent input
  - [ ] TDD: block-scalar content lines containing tabs are NOT rejected (the guard only covers structural indentation) and still round-trip
  - [ ] MECHANICAL: the fix lives in goc/_vendor/yaml_lite.py and matches the docstring contract at line 21
  - [ ] `uv run goc validate` passes and the full regression suite is green
worker: {who: "claude[bot]", where: main}
---

# Tab-indented frontmatter silently misparses instead of raising

## Location

`goc/_vendor/yaml_lite.py:21` (docstring contract) vs.
`goc/_vendor/yaml_lite.py:85-87` (`_indent`).

## What's broken

The module docstring states tab indentation is a hard error:

```text
Unsupported (raises ParseError):
  - Anchors (&foo), aliases (*foo), tags (!!str)
  - Multi-document streams
  - Folded scalars (>)
  - Tabs as indentation          # ← line 21
```

But `_indent()` measures indentation with `lstrip()`, which strips
tabs too, counting a leading tab as one indentation character — and
there is no tab guard anywhere in the parser:

```python
@staticmethod
def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())
```

So tab-indented YAML parses without raising. Worse than a missed
error, a tab+space-indented key is silently promoted to a top-level
sibling, corrupting the document structure.

## Empirical evidence

`uv run python deck/<title>/reproduce.py`:

```text
case 1 (nested via tab):   {'parent': {'child': 'v'}}         (expected ParseError)
case 2 (sequence via tab): {'items': ['a', 'b']}              (expected ParseError)
case 3 (tab+space indent): {'a': 1, 'b': 2}                   (expected ParseError; 'b' silently promoted to top level)
RESULT: FAIL — tab indentation parsed silently in all 3 cases
```

## Why it matters

`yaml_lite.safe_load` is the parser for every card's frontmatter
(`engine.py:161`), `config.yaml` (`engine.py:89`, `4161`, `4163`),
and `schema.yaml` (`engine.py:480`). The engine's own emitter never
produces tabs, so this only bites **hand-edited or externally-migrated
cards** — exactly the inputs where the documented loud-failure contract
matters most. A card whose frontmatter was hand-edited with a tab
doesn't get rejected by `goc validate`; it loads with a silently wrong
structure (case 3 drops a field's nesting), defeating the validator's
purpose of catching frontmatter drift. The whole reason this parser
enumerates an "Unsupported (raises ParseError)" list is to fail loud
rather than misparse; tab indentation is the one entry that doesn't
honor it.

## Fix

Add the tab-indentation guard at the single structural chokepoint:
`_peek()`. Every structurally-significant line (mapping keys, sequence
items, value continuations) is fetched through `_peek()`, while
block-scalar content is read directly from `self._lines` (line 182)
and never passes through `_peek()`. So guarding there rejects tab
indentation exactly where indentation is structural, without touching
literal block-scalar content (where leading tabs beyond the block
indent are legitimate content).

```python
def _peek(self) -> str | None:
    while self._pos < len(self._lines):
        line = self._lines[self._pos]
        bare = line.rstrip().lstrip()
        if bare and not bare.startswith("#"):
            lead = line[: len(line) - len(line.lstrip())]
            if "\t" in lead:
                raise ParseError(
                    f"line {self._pos + 1}: tabs are not allowed as indentation"
                )
            return self._lines[self._pos].rstrip()
        self._pos += 1
    return None
```

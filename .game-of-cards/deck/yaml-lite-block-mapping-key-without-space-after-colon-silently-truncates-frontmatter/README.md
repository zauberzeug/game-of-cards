---
title: yaml-lite-block-mapping-key-without-space-after-colon-silently-truncates-frontmatter
summary: "The vendored yaml_lite parser only treats a `:` as a block-mapping key separator when a space/tab follows it, so a hand-edited line like `status:open` (no space) is unrecognized. `_parse_block_mapping` then silently `break`s on that line, dropping it AND every key below it from the document — no error. This is the one same-indent silent-truncation hole left in the parser's otherwise loud-fail posture (tabs, over-indent, and block-scalar headers all raise)."
status: active
stage: null
contribution: medium
created: "2026-06-24T13:17:44Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — `safe_load("title: foo\nstatus:open\ncontribution: medium")` raises ParseError instead of returning `{'title': 'foo'}`
  - [ ] TDD: a test in tests/test_yaml_lite.py asserts a same-indent block-mapping line with a colon but no following space (`a: 1\nb:2\nc: 3`) raises ParseError, and a bare-scalar same-indent line (no colon at all) also raises
  - [ ] TDD: existing valid-mapping round-trips still pass (the full tests/test_yaml_lite.py suite stays green)
  - [ ] MECHANICAL: `uv run python -m unittest discover -s tests` passes; `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# yaml-lite-block-mapping-key-without-space-after-colon-silently-truncates-frontmatter

## Location

`goc/_vendor/yaml_lite.py:126-129` (`_parse_block_mapping`), root cause at
`goc/_vendor/yaml_lite.py:441-442` (`_split_key`).

## What's broken

`_split_key` only counts a `:` as a key separator when the next character is a
space or tab, or the colon is at end-of-line:

```python
elif c == ":":
    if i + 1 < len(bare) and bare[i + 1] in (" ", "\t"):
        rest = bare[i + 2 :].lstrip()
        return bare[:i], _strip_comment(rest)
    if i + 1 == len(bare):
        return bare[:i], ""
return None, ""
```

So a line like `status:open` (no space after the colon) returns `(None, "")`.
Back in `_parse_block_mapping`, that triggers a **silent** termination:

```python
bare = line.lstrip()
key, rest = _split_key(bare)
if key is None:
    break          # <-- drops this line AND every key below it, no error
self._pos += 1
result[key] = self._resolve_value(rest, indent)
```

This is inconsistent with the parser's own documented loud-fail posture. The
guard immediately above it — for a line indented *more* than the mapping —
`raise`s a `ParseError` (lines 113-125), as do the tab-indentation guard in
`_peek` (lines 90-93) and the ambiguous block-scalar-indent guard. A
same-indent malformed key is the one silent-truncation hole left in that
posture, and it is exactly the failure mode the over-indent guard's own comment
says it exists to prevent ("a bare plain-scalar continuation … would otherwise
truncate every following key").

## Empirical evidence

See `reproduce.py`. Live confirmation:

```
case1: {'title': 'foo'}          # safe_load('title: foo\nstatus:open\ncontribution: medium')
case2: {'a': 1}                  # safe_load('a: 1\nb:2\nc: 3')
over-indent (control, raises):   ParseError   # safe_load('a: 1\n  b: 2')
```

`status:open` and every key after it are silently dropped, while the analogous
over-indent case correctly raises.

## Why it matters

`safe_load` is the read path for every card's frontmatter
(`engine.parse_frontmatter` at `engine.py:161` calls it on the text between the
`---` fences) and for `.game-of-cards/config.yaml` (`engine.py:89`, `4348`,
`4350`). Card frontmatter is normally machine-emitted by `emit_frontmatter`,
which always writes `key: value` with a space — so the shipping emit path never
produces the offending shape. The reachability is the *hand-edit / external
tooling* path: a contributor or a non-goc tool that writes `status:open`,
`human_gate:none`, or any colon-without-space line loses that field plus the
status, tags, DoD, and edges below it on the next read — silently, with the
card still appearing valid. `ParseError` is a `ValueError` subclass, so
`parse_frontmatter` already rewraps it into a clean `FrontmatterError`, exactly
as it does for the tab and over-indent cases.

This completes a family of same-shape fixes that are already closed for the
adjacent cases: [yaml-lite-drops-same-indent-block-sequence-and-truncates-frontmatter](../yaml-lite-drops-same-indent-block-sequence-and-truncates-frontmatter/)
(same-indent block *sequence* items),
[yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising](../yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising/)
(*over*-indented lines), and
[yaml-lite-flow-mapping-drops-pairs-without-a-space-after-the-colon](../yaml-lite-flow-mapping-drops-pairs-without-a-space-after-the-colon/)
(*flow* mapping `{who:rodja}`). None covers the same-indent block-*mapping* key
with no space after the colon.

## Fix

In `_parse_block_mapping`, replace the silent `break` on `key is None` with a
`raise ParseError`, mirroring the adjacent over-indent guard. Any line that
reaches this point is at the mapping indent (the `curr < indent` dedent and
`curr > indent` over-indent cases are already handled above) and is therefore a
malformed mapping entry — either a colon with no following space, or a bare
scalar with no colon at all. Both are invalid YAML in block-mapping context and
should fail loud rather than truncate the document. The message should name the
missing-space-after-colon as the common cause.

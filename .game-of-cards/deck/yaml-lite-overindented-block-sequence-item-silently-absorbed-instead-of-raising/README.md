---
title: yaml-lite-overindented-block-sequence-item-silently-absorbed-instead-of-raising
status: active
stage: null
contribution: medium
created: "2026-06-22T19:31:36Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
summary: |
  The vendored yaml_lite parser's block-sequence loop only breaks on a
  less-indented line; a MORE-indented `- item` line is silently accepted
  as a same-level sequence item. This is the block-sequence analogue of
  the mapping over-indent gap fixed in 119cf31, which added a
  `curr > indent` fail-loud guard to _parse_block_mapping but left
  _parse_block_sequence untouched. The four edge fields (advances,
  advanced_by, supersedes, superseded_by) are block sequences, so a
  hand-edited card with an over-indented edge item is mis-parsed instead
  of rejected, and goc validate does not catch it.
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero once fixed — an over-indented block-sequence item raises ParseError instead of being silently absorbed
  - [ ] TDD: a unit test in tests/test_yaml_lite.py asserts ParseError is raised for an over-indented sequence item
  - [ ] TDD: existing valid block sequences, nested sequences, and inline-map sequence items still parse unchanged (regression suite stays green)
  - [ ] MECHANICAL: the fix lands in goc/_vendor/yaml_lite.py only; plugin mirrors regenerate via the sync hook
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# yaml-lite-overindented-block-sequence-item-silently-absorbed-instead-of-raising

## Location

`goc/_vendor/yaml_lite.py:136-147` — the `_parse_block_sequence` loop.

## What's broken

Commit `119cf31`
([yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising](../yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising/),
done) added a `curr > indent` fail-loud guard to `_parse_block_mapping`
so an over-indented line is rejected rather than silently mangled. The
**identical guard was never added to `_parse_block_sequence`**, which
still only handles the less-indented case:

```python
def _parse_block_sequence(self, indent: int) -> list:
    result: list[Any] = []
    while True:
        line = self._peek()
        if line is None:
            break
        curr = self._indent(line)
        if curr < indent:        # only the LESS-indented case breaks
            break
        bare = line.lstrip()
        if not (bare.startswith("- ") or bare == "-"):
            break
        self._pos += 1
        ...
```

There is **no branch for `curr > indent`**. An over-indented `- item`
line satisfies neither break condition — `curr` is not `< indent`, and
the line still starts with `- ` — so it is consumed as a same-level
sequence item. In every valid parse path the top-of-loop line is at
`<= indent`: a nested sequence's more-indented items are consumed in
full by the recursive `_parse_block_sequence(ni)` call at line 172
before control returns here. A `curr > indent` line at the top of the
loop is therefore malformed, exactly as in the mapping case.

## Empirical evidence

See `reproduce.py`. Verbatim output on a clean checkout:

```
Case — over-indented block-sequence item:
  input: 'advances:\n  - first-target\n      - second-target\ncontribution: high\n'
  yaml_lite: {'advances': ['first-target', 'second-target'], 'contribution': 'high'}   (second-target WRONGLY absorbed as a same-level item)
  for contrast, the mapping analogue 'status: open\n    rogue: value\n' correctly raises ParseError

DEFECT CONFIRMED: yaml_lite silently absorbs the over-indented sequence item; it does not raise.
```

## Why it matters

`yaml_lite.safe_load` is the production frontmatter reader — PyYAML was
removed in `replace-pyyaml-with-vendored-parser`, and this parser is
mirrored into all four plugin payloads. Every card read goes
`engine.load_card → parse_frontmatter (engine.py:144) → safe_load`.

Reachability: the emitter never produces over-indented lines, so this
shape arises from a **hand-edited or externally-tooled card README**.
The four bidirectional-edge list fields (`advances`, `advanced_by`,
`supersedes`, `superseded_by`) are emitted as block sequences and are
the most likely place for a stray leading-space copy/paste artifact. A
mis-indented edge item still parses to a value — just one absorbed into
the wrong list level — so `goc validate` reports a clean parse of a
document the author did not write. The recent mapping fix declared this
silent-corruption class unacceptable; the sequence parser is the open
sibling of that same contract.

This is the block-sequence analogue of
[yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising](../yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising/)
(done — mapping `curr > indent` guard) and is distinct from
[yaml-lite-drops-same-indent-block-sequence-and-truncates-frontmatter](../yaml-lite-drops-same-indent-block-sequence-and-truncates-frontmatter/)
(done — the *opposite* failure mode, same-indent items dropped). Neither
covers an over-indented sequence item.

## Fix

In `_parse_block_sequence`, after the `curr < indent` break, a
more-indented line raises instead of being treated as a same-level
item, mirroring `_parse_block_mapping`:

```python
        curr = self._indent(line)
        if curr < indent:
            break
        if curr > indent:
            raise ParseError(
                f"line {self._pos + 1}: line is indented {curr}, more than "
                f"the surrounding sequence at {indent}; unexpected indentation"
            )
```

This is safe: nested sequences and inline-map items are consumed by the
recursion / `_parse_block_mapping` before control returns to the top of
the loop, so a `curr > indent` line is always malformed. Raising matches
the parser's fail-loud contract and the precedent set by the mapping
guard, the tab guard in `_peek`, and the block-scalar ambiguous-indent
`ParseError`.

Regression coverage lands in `tests/test_yaml_lite.py`. The edit is
confined to `goc/_vendor/yaml_lite.py`; the plugin mirrors regenerate
byte-for-byte via `scripts/sync_plugin_assets.py`.

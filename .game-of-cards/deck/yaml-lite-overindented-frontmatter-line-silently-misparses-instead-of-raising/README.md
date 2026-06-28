---
title: yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising
status: done
stage: null
contribution: medium
created: "2026-06-22T15:13:42Z"
closed_at: "2026-06-22T15:18:09Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
summary: |
  The vendored yaml_lite parser only breaks its mapping loop on a
  less-indented line; a MORE-indented line is silently accepted as a
  sibling key — promoting a nested key to top level, or, for a
  bare-scalar continuation, silently truncating every following key.
  PyYAML raises ScannerError on the same input. The sibling tab-indent
  guard fixed tabs but not spaces.
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — both over-indent cases raise ParseError instead of silently mis-parsing
  - [x] TDD: a unit test in tests/ asserts ParseError is raised for an over-indented mapping key and for an over-indented bare-scalar continuation
  - [x] TDD: existing valid block mappings, nested mappings, block sequences, and block scalars still parse unchanged (regression suite stays green)
  - [x] MECHANICAL: the fix lands in goc/_vendor/yaml_lite.py only; plugin mirrors regenerate via the sync hook
worker: {who: "claude[bot]", where: main}
---

# yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising

## Location

`goc/_vendor/yaml_lite.py:110-118` — the `_parse_block_mapping` loop.

## What's broken

`_parse_block_mapping` decides whether the next line is a sibling key,
the end of the mapping, or an error by comparing indentation against
the mapping's established `indent`. But it only handles the
*less-indented* case:

```python
def _parse_block_mapping(self, indent: int) -> dict:
    result: dict[str, Any] = {}
    while True:
        line = self._peek()
        if line is None:
            break
        curr = self._indent(line)
        if curr < indent:
            break
        bare = line.lstrip()
        key, rest = _split_key(bare)
        if key is None:
            break
        self._pos += 1
        result[key] = self._resolve_value(rest, indent)
    return result
```

There is **no branch for `curr > indent`**. Once a value has been
resolved, control returns to the top of the loop; in well-formed YAML
the next structural line is always at `<= indent` (a sibling, or the
parent's territory). A line at `curr > indent` is malformed — a key
indented more than its surrounding mapping with no parent value
indicator opening a nested scope. The loop nonetheless falls through
to `_split_key` and treats it as an ordinary sibling.

This produces two distinct silent corruptions:

1. **Over-indented key promoted to sibling.** A nested-looking key is
   flattened up to the parent level instead of raising:

   ```
   status: open
     human_gate: decision
   ```

   yaml_lite returns `{'status': 'open', 'human_gate': 'decision'}` —
   `human_gate` silently promoted to top level. PyYAML raises
   `ScannerError: mapping values are not allowed here`.

2. **Over-indented bare continuation truncates the rest of the
   document.** A plain-scalar value followed by a more-indented line
   that lacks a colon hits `_split_key(...) is None → break`, abandoning
   every key that follows:

   ```
   summary: hello
     world
   status: open
   ```

   yaml_lite returns `{'summary': 'hello'}` — the ` world` line is
   dropped **and `status: open` never gets parsed**. PyYAML folds it to
   `{'summary': 'hello world', 'status': 'open'}`.

The parser's documented contract is to *fail loud* on inputs it does
not faithfully support (see the tab guard in `_peek` and the
ambiguous-indent `ParseError` in `_parse_block_scalar`). Over-indented
mapping lines violate that contract: they are neither faithfully parsed
nor rejected — they are silently mangled.

## Empirical evidence

See `reproduce.py`. Verbatim output on a clean checkout:

```
Case 1 — over-indented mapping key:
  input: 'status: open\n  human_gate: decision\n'
  yaml_lite: {'status': 'open', 'human_gate': 'decision'}   (human_gate WRONGLY promoted to top level)
  PyYAML:    raises ScannerError

Case 2 — over-indented bare continuation:
  input: 'summary: hello\n  world\nstatus: open\n'
  yaml_lite: {'summary': 'hello'}   (world dropped AND status:open silently truncated)
  PyYAML:    {'summary': 'hello world', 'status': 'open'}

DEFECT CONFIRMED: yaml_lite silently mis-parses both; neither raises.
```

## Why it matters

`yaml_lite.safe_load` is the production frontmatter reader — PyYAML was
removed in `replace-pyyaml-with-vendored-parser`, and this parser is
mirrored into all four plugin payloads. Every card read goes
`engine.load_card → parse_frontmatter (engine.py:144) → safe_load`.

Reachability: the emitter never produces over-indented lines, so this
shape arises from a **hand-edited or externally-tooled card README** —
a stray leading space on a frontmatter line is one of the most common
copy/paste artifacts. When it happens, `goc validate` does **not** catch
it (Case 1 still parses to a value, just the wrong one — a nested
`human_gate` becomes a real top-level gate; Case 2 silently loses
fields such as `status`/`closed_at`, changing how the card schedules and
validates). A reader who indented a sub-key by mistake gets a card that
parses "successfully" into a different document than they wrote.

This is the space-indent analogue of
[tab-indented-frontmatter-silently-misparses-instead-of-raising](../tab-indented-frontmatter-silently-misparses-instead-of-raising/)
(done — tab guard in `_peek`) and is distinct from
[yaml-lite-drops-same-indent-block-sequence-and-truncates-frontmatter](../yaml-lite-drops-same-indent-block-sequence-and-truncates-frontmatter/)
(done — same-indent block sequences). Neither covers an over-indented
mapping key or bare continuation.

## Fix (applied)

In `_parse_block_mapping`, after the `curr < indent` break, a
more-indented line now raises instead of being treated as a sibling:

```python
        curr = self._indent(line)
        if curr < indent:
            break
        if curr > indent:
            raise ParseError(
                f"line {self._pos + 1}: line is indented {curr}, more than "
                f"the surrounding mapping at {indent}; unexpected indentation"
            )
```

This is safe: in every valid parse path the top-of-loop line is at
`<= indent`. Nested mappings/sequences/block scalars are parsed by
`_resolve_value`, which consumes all of their more-indented lines before
returning, so a `curr > indent` line at the top of the mapping loop is
always malformed. Raising matches the parser's fail-loud contract and
the precedent set by the tab guard and the block-scalar
ambiguous-indent `ParseError`.

Regression coverage lands in `tests/test_yaml_lite.py`
(`OverIndentedMappingRejectionTest`): both over-indent cases raise, and
valid nested / deeply-nested mappings still parse unchanged. The edit is
confined to `goc/_vendor/yaml_lite.py`; the three plugin mirrors were
regenerated byte-for-byte by `scripts/sync_plugin_assets.py`.

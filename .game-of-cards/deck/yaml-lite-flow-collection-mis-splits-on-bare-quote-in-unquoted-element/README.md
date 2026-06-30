---
title: yaml-lite-flow-collection-mis-splits-on-bare-quote-in-unquoted-element
summary: "`_split_flow` flips quote-mode on ANY quote char mid-element, with no guard that the element is genuinely quoted. A flow mapping/sequence element carrying a bare apostrophe (`{who: o'connor, where: x}`) swallows the comma separator and drops every following field — `where` is silently lost. The sibling scanner `_strip_comment` already carries the element-start guard this one lacks."
status: active
stage: null
contribution: medium
created: "2026-06-30T02:11:27Z"
closed_at: null
human_gate: none
advances:
  - yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting
advanced_by: []
tags: [bug, api-contract, infra, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — a bare apostrophe in a flow mapping/sequence element no longer swallows the comma separator.
  - [ ] TDD: `parse_frontmatter` on `worker: {who: o'connor, where: feature/x}` yields `{'who': "o'connor", 'where': "feature/x"}` (no field dropped).
  - [ ] TDD: regression — a genuinely quoted element with an internal comma (`"x, y", z`) still splits into two parts (the comma stays content).
  - [ ] MECHANICAL: `_split_flow` only enters quote-mode at element start (or inside a nested flow collection), matching the `quoted`/`flow` gate `_strip_comment` already uses.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` green; `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green (vendored parser mirrored into the plugin payloads).
worker: {who: "claude[bot]", where: main}
---

# yaml-lite-flow-collection-mis-splits-on-bare-quote-in-unquoted-element

## Location

`goc/_vendor/yaml_lite.py:462-464` — the quote-entry arm of `_split_flow`.

## What's broken

`_split_flow` splits comma-separated flow content while tracking quote
state so a comma *inside* a quoted element is not treated as a separator.
But its quote-entry arm flips quote-mode on **any** quote character, with
no check that the quote actually opens the element:

```python
        elif c in ('"', "'"):
            in_q = c
            buf.append(c)
```

So a bare apostrophe that is ordinary content — the `'` in `o'connor`, a
`5 o'clock`, an `O'Brien` — is mistaken for the start of a quoted scalar.
From that apostrophe on, every character (including the top-level comma)
is swallowed into the "quoted" run, so the element never ends and the
following key/element is lost.

The sibling scanner `_strip_comment` (`yaml_lite.py:519-520`, `537`)
already learned this exact lesson and carries an element-start guard:

```python
    flow = text[:1] in ("[", "{")
    quoted = text[:1] in ('"', "'")
    ...
        elif (quoted or flow) and c in ('"', "'"):
            in_q = c
```

with the comment spelling out the rule: *"In a bare value a lone quote
char — the apostrophe in `don't`, the `'` in `5 o'clock` — is ordinary
content and must not flip into quote mode."* `_split_flow` never got the
same gate, so it still treats a bare apostrophe as a quote opener.

## Empirical evidence

`reproduce.py` on a clean checkout (defect fires):

```
_split_flow("who: o'connor, where: feature/x")
  -> ["who: o'connor, where: feature/x"]
  FAIL: expected 2 elements, got 1 (comma swallowed by bare quote)
_split_flow("a'b, c")
  -> ["a'b, c"]
  FAIL: expected 2 elements, got 1
parse_frontmatter worker -> {'who': "o'connor, where: feature/x"}
  FAIL: worker mapping corrupted (where dropped / who mangled)
_split_flow('"x, y", z')
  -> ['"x, y"', ' z']
  ok: quoted internal comma preserved

RESULT: FAIL (defect fires)
```

The `where` field is silently dropped and `who` is corrupted to
`"o'connor, where: feature/x"`.

## Why it matters — reachability

`_split_flow` is the splitter behind both `_parse_flow_mapping`
(`yaml_lite.py:433`, used for the `worker` mapping) and
`_parse_flow_sequence` (`yaml_lite.py:411`, used for `tags`). Every
`goc` read flows through `parse_frontmatter`, and the vendored parser is
mirrored byte-for-byte into all three plugin payloads.

The emitter is not the source of the bad input: `_emit_worker` /
`_yaml_inline` quote an apostrophe-bearing value (`{who: "o'connor", ...}`),
so an emitter→parse round-trip is fine — the quoted element starts with
`"` and the existing logic handles it. The offending input is
**hand-authored** frontmatter. AGENTS.md documents the `worker` field as
free-form, with a `{who, where}` mapping form, and explicitly tells
humans to edit frontmatter by hand. A name with an apostrophe
(`o'connor`, `O'Brien`) written without quotes — exactly the lenient
shape a parser is supposed to accept — silently loses the `where` field
and corrupts `who` with no error.

This is the same lenient-parser-surface reachability the prior sibling
cards documented (e.g.
[yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value](../yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value/),
[yaml-lite-flow-collection-mis-splits-on-backslash-escaped-quote](../yaml-lite-flow-collection-mis-splits-on-backslash-escaped-quote/)).
It is one more concrete instance of the drift catalogued by
[yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/):
a fix landed on `_strip_comment` was never propagated to `_split_flow`.
This card fixes the live instance now; the meta-fix card remains the way
to stop the next divergence.

## Fix

Give `_split_flow` the element-start guard that `_strip_comment` already
uses. Track whether the current element began with a quote (or is a
nested flow collection), and only enter quote-mode for such elements; a
quote that appears mid-element is bare content. Reset the per-element
"started with a quote" flag at each top-level comma (and at the start of
the scan). The four existing yaml_lite regression tests plus the new
ones in this card's DoD are the contract the change must preserve.

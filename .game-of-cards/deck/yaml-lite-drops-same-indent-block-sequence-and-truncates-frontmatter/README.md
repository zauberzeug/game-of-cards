---
title: yaml-lite-drops-same-indent-block-sequence-and-truncates-frontmatter
summary: "The vendored yaml_lite parser requires block-sequence items to be indented strictly more than their parent key, but YAML (and PyYAML) accept items at the SAME indent. A card written with `advanced_by:\\n- item` loses that value (resolves to None) AND every frontmatter key after it (tags, definition_of_done) is silently dropped — no error. Hand-authored or externally-tooled cards lose their edges, tags, and DoD on every read."
status: active
stage: null
contribution: high
created: "2026-05-27T09:21:42Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a same-indent block sequence (`key:\n- item`) parses to a list, not None.
  - [ ] TDD: keys that follow a same-indent block sequence (`tags`, `definition_of_done`) survive parsing instead of being dropped.
  - [ ] TDD: an inline-map item at same indent (`worker:\n- who: x`) and a nested same-indent sequence both round-trip; the existing strictly-more-indented form is unchanged (no regression).
  - [ ] MECHANICAL: `uv run goc validate` is clean and the plugin engine mirrors are re-synced (yaml_lite is vendored into every plugin payload).
worker: {who: "claude[bot]", where: main}
---

# yaml_lite drops a same-indent block sequence and truncates the rest of the frontmatter

## Location

`goc/_vendor/yaml_lite.py:250-260` — `_resolve_value`, the empty-`rest`
branch that decides whether a key's value lives on following lines:

```python
if rest == "":
    next_line = self._peek()
    if next_line is None:
        return None
    ni = self._indent(next_line)
    if ni <= parent_indent:          # <-- rejects same-indent sequences
        return None
    nb = next_line.lstrip()
    if nb.startswith("- ") or nb == "-":
        return self._parse_block_sequence(ni)
    return self._parse_block_mapping(ni)
```

Reached for every card via `parse_frontmatter` (`goc/engine.py:160`),
and also used to load `schema.yaml` (`:385`) and `config.yaml`
(`:88`, `:3295`).

## What's broken

YAML lets a block-sequence's `- item` lines sit at the **same**
indentation as the parent mapping key. This is valid, common, and what
PyYAML produces a list for:

```yaml
advanced_by:
- upstream-card
```

`yaml_lite` requires sequence items to be *strictly more* indented than
the key (`ni <= parent_indent` returns `None`). Two failures compound:

1. The key resolves to `None` — the value is lost.
2. The un-indented `- upstream-card` line is then handed back to
   `_parse_block_mapping`, where `_split_key` returns `None` on a `-`
   line and the loop `break`s (`yaml_lite.py:98-99`) — so **every
   subsequent key is dropped too**, never even appearing in the dict.

There is no error. The card just silently loses its dependency edges,
tags, and Definition-of-Done.

This contradicts the parser's own contract. `yaml_lite`'s module
docstring frames it as a PyYAML-subset stand-in for frontmatter, and
the engine aliases it as `import ... as yaml`; AGENTS.md's card-authoring
rules instruct authors to write `advances`/`advanced_by` in "block-style
(one `- item` per line)" without mandating extra indentation. A human
following that guidance literally produces frontmatter that parses to
garbage.

goc's own `emit_frontmatter` writes 2-space-indented items, so cards
the tool round-trips itself are safe — which is exactly why this has
gone unnoticed. The exposure is hand-authored cards, cards produced by
external YAML tooling, and any consumer who reads the AGENTS.md
convention literally.

## Empirical evidence

`uv run python deck/<this-card>/reproduce.py`:

```
Input frontmatter (same-indent block sequences, valid YAML):
title: example
advanced_by:
- upstream-card
tags:
- bug
- infra
definition_of_done: |
  - [ ] do the thing

yaml_lite.safe_load result:
  'title': 'example'
  'advanced_by': None

Keys lost entirely: ['tags', 'definition_of_done']
Keys with wrong value: ['advanced_by']

FAIL: same-indent block sequence dropped and frontmatter truncated.
  - 'advanced_by' resolves to None instead of ['upstream-card']
  - 'tags' and 'definition_of_done' vanish from the dict entirely
  -> card loses its dependency edges, tags, and DoD on every read.
```

## Why it matters

A dropped `advanced_by` breaks the deck's scheduler axis (the card no
longer derives as dependency-blocked) and its record axis (a cold
reader can't reconstruct the edge). A dropped `definition_of_done`
turns the card into a freeform-DoD card that `goc done --force` can
close with no checklist enforcement — the closure contract evaporates.
A dropped `tags` removes it from every tag-filtered queue. All silent.

A second, related amplifier (worth a sibling card if confirmed, not
fixed here): the relationship/decision verbs (`decide`, `advance`,
`unadvance`) re-emit the whole frontmatter via `emit_frontmatter`
rather than the surgical `mutate_frontmatter_field` path. Run on a card
whose frontmatter yaml_lite mis-parses, they would **persist** the
truncated version to disk — promoting this from a read-time bug to
durable data loss.

## Fix

In `_resolve_value`, accept a block sequence whose items are at the same
indent as the parent key (the block-mapping branch should stay
strictly-more-indented to avoid swallowing siblings). Concretely: when
`rest == ""` and the next line is a sequence item (`- ` / `-`) at
`ni == parent_indent`, parse it as a block sequence at `ni` rather than
returning `None`. The mapping-continuation branch must still require
`ni > parent_indent`. Add regression cases covering same-indent scalar
sequences, same-indent inline-map item sequences, and confirm the
strictly-more-indented form is untouched. yaml_lite is vendored into
all plugin payloads, so re-run the plugin asset sync.

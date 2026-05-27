---
title: yaml-lite-truncates-flow-collection-with-hash-in-quoted-element
summary: "yaml_lite's `_strip_comment` only enters quote-tracking mode when the *whole* value starts with a quote. An inline flow collection starts with `[` or `{`, so quote-tracking stays off and a ` #` inside a quoted element is treated as a comment and stripped — corrupting `tags: [\"a #b\", c]` to `['[\"a']` and silently dropping `worker: {who: x, where: \"br #1\"}` to `{}`. goc's own emitter produces these exact strings, so a card written by goc round-trips to data loss on reload."
status: active
stage: null
contribution: medium
created: "2026-05-27T09:34:08Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — `safe_load('tags: ["a #b", c]\nworker: {who: x, where: "br #1"}')` returns `{'tags': ['a #b', 'c'], 'worker': {'who': 'x', 'where': 'br #1'}}` (no truncation, no dropped field). Fails before the fix, passes after.
  - [ ] TDD: regression guard — the sibling fix's behavior is preserved: a bare value with an unbalanced lone quote still strips its trailing comment (`title: don't  # note` → `don't`), and a `#` inside a *balanced* quoted scalar is still NOT stripped (`a: "x # y"` → `x # y`).
  - [ ] TDD: emit→parse round-trip is lossless for the cases above — `emit_frontmatter({'tags': ['a #b','c'], 'worker': {'who':'x','where':'br #1'}})` reparses to an equal dict.
  - [ ] PROCESS: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green (the vendored parser is mirrored into the plugin payloads).
worker: {who: "claude[bot]", where: main}
---

# yaml-lite truncates inline flow collections when a quoted element contains a hash

## Location

`goc/_vendor/yaml_lite.py:395-414` — `_strip_comment`, reached from `_split_key`
(`goc/_vendor/yaml_lite.py:389`) for every scalar value before it is parsed.

## What's broken

```python
def _strip_comment(text: str) -> str:
    """Remove trailing `# comment` (or leading `#` comment) from a value."""
    if text.startswith("#"):
        return ""
    quoted = text[:1] in ('"', "'")          # <-- only TRUE for a fully-quoted scalar
    in_q: str | None = None
    for i, c in enumerate(text):
        if in_q:
            if c == in_q:
                in_q = None
        elif quoted and c in ('"', "'"):      # <-- quote-tracking gated on `quoted`
            in_q = c
        elif c == "#" and i > 0 and text[i - 1] in (" ", "\t"):
            return text[:i].rstrip()
    return text
```

The `quoted` gate was added by the closed card
[`yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value`](../yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value/)
to stop a lone apostrophe in a *bare* scalar (`don't`) from flipping into quote
mode and suppressing comment detection. That fix is correct for bare scalars,
but it created the complementary defect for **flow collections**: an inline list
`[...]` or mapping `{...}` starts with `[`/`{`, so `quoted` is `False`,
quote-tracking never turns on, and the first ` #` — even one sitting *inside a
quoted element* of the collection — is treated as a trailing comment and the
value is truncated there. The scanner also tracks no bracket depth.

Result:

- `tags: ["a #b", c]` → parsed value `['["a']` (truncated at ` #`, second
  element lost, first element left as the literal substring `["a`).
- `worker: {who: x, where: "br #1"}` → parsed value `{}` — the whole mapping is
  truncated to `{who: x, where: "br` which fails to parse as a mapping and the
  **entire field silently vanishes**.

This is not merely a hand-edit hazard: goc's emitter *produces* these exact
strings. `_yaml_inline` (`goc/engine.py:197`) quotes any value matching
`_YAML_NEEDS_QUOTE` (which includes `#`), so `emit_frontmatter` writes
`where: "br #1"` inside the flow mapping and `"a #b"` inside the flow list —
output its own parser cannot read back.

## Empirical evidence

```
INPUT YAML:
title: x
tags: ["a #b", c]
worker: {who: x, where: "br #1"}

safe_load -> {'title': 'x', 'tags': ['["a'], 'worker': {}}

  [FAIL] tags corrupted: ['["a'] != ['a #b', 'c']
  [FAIL] worker dropped/corrupted: {} != {'who': 'x', 'where': 'br #1'}

emit_frontmatter(fm):
---
title: x
tags: ["a #b", c]
worker: {who: x, where: "br #1"}
---

reparsed -> {'title': 'x', 'tags': ['["a'], 'worker': {}}
  [FAIL] emit -> parse round-trip is lossy (emitter output its own parser cannot read)

RESULT: FAIL — defect reproduced
```

(`uv run python .game-of-cards/deck/yaml-lite-truncates-flow-collection-with-hash-in-quoted-element/reproduce.py`)

## Why it matters

The frontmatter parser/emitter is the storage contract for every card. An
emitter that produces output its own parser silently corrupts is a contract
violation, and the `worker` failure mode is the worst kind — total field loss
with no error. A `worker.where` branch name or a free-form `who` capability tag
containing ` #` (e.g. a worktree label `gpu #2`) is reclassified as unworked on
the next load. The blast radius is narrower than the apostrophe sibling (only
flow collections with a quoted ` #` element trigger it) but the failure is
silent and lossy rather than a retained stray comment.

## Fix

Make `_strip_comment` flow-aware. Two viable shapes:

1. Track bracket/brace depth and enable quote-tracking unconditionally while
   inside a flow collection (`depth > 0`), so a `#` is only treated as a comment
   when it is outside both quotes and brackets. This generalizes the `quoted`
   gate rather than replacing it.
2. Detect a flow-collection value (`text[:1] in '[{'`) up front and route it
   through a depth+quote-aware scan, keeping the existing bare-scalar path
   untouched.

Either preserves the sibling card's bare-scalar behavior. Do NOT apply the fix
in this card — file records the defect; `pull-card` implements.

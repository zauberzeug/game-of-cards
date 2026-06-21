---
title: yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value
summary: "yaml-lite's `_strip_comment` tracks quote state to avoid stripping a `#` inside a quoted run, but on a bare (unquoted) scalar value containing a lone `'` or `\"` (e.g. an apostrophe) it enters quote mode and never exits, so a trailing `# comment` is never recognized and is kept as part of the value. Real YAML strips that comment. Confirmed: `safe_load(\"title: don't  # note\")` returns `{'title': \"don't  # note\"}`. Narrow blast radius — goc's emitter quotes values containing `#`, so it only bites hand-edited frontmatter / config.yaml / canonical-tags.md."
status: done
stage: null
contribution: low
created: "2026-05-26T22:28:42Z"
closed_at: "2026-05-26T23:07:10Z"
human_gate: none
advances:
  - yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a `reproduce.py` asserts `safe_load("title: don't  # note") == {"title": "don't"}` (comment stripped, matching real YAML); fails before the fix, passes after
  - [x] TDD: regression guard — a `#` inside a properly *balanced* quoted run is still NOT stripped (e.g. `a: "x # y"` → `"x # y"`), and a bare value with no quote still strips its comment
  - [x] PROCESS: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green (the vendored parser is mirrored into the plugin payloads)
worker: {who: "claude[bot]", where: main}
---

# yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value

## Location

`goc/_vendor/yaml_lite.py:359-372` — `_strip_comment`; reached from
`_split_key` (`goc/_vendor/yaml_lite.py:353`) for every bare scalar value.

## What's broken

```python
def _strip_comment(text: str) -> str:
    """Remove trailing `# comment` (or leading `#` comment) from a value."""
    if text.startswith("#"):
        return ""
    in_q: str | None = None
    for i, c in enumerate(text):
        if in_q:
            if c == in_q:
                in_q = None
        elif c in ('"', "'"):
            in_q = c
        elif c == "#" and i > 0 and text[i - 1] in (" ", "\t"):
            return text[:i].rstrip()
    return text
```

The quote-tracking is meant to keep a `#` *inside a quoted run* from being
treated as a comment. But this function runs on the **bare (unquoted)**
value after `_split_key` has already separated the key. A lone quote
character in that bare value — an apostrophe in `don't`, the `'` in
`5 o'clock` — flips `in_q` on and, with no matching closing quote, it never
flips off. From that character onward the `# comment` branch is
unreachable, so the comment is silently retained in the value.

Real YAML treats `title: don't  # note` as value `don't` with a stripped
comment; yaml-lite keeps `don't  # note`.

## Empirical evidence

```
>>> from goc._vendor.yaml_lite import safe_load
>>> safe_load("title: don't  # note")
{'title': "don't  # note"}          # expected {'title': "don't"}
>>> safe_load("a: 5 o'clock # x")
{'a': "5 o'clock # x"}               # expected {'a': "5 o'clock"}
>>> safe_load("b: plain value  # cmt")
{'b': 'plain value'}                 # control: no quote → comment stripped OK
```

## Why it matters

Lower blast radius than the block-scalar round-trip family: goc's own
emitter quotes any value containing `#`, so a goc-managed card never round-
trips through this path. It bites **hand-edited** surfaces parsed by the
same `safe_load` — frontmatter edited by hand, `.game-of-cards/config.yaml`,
and the `canonical_tags:` block in `canonical-tags.md` — where an author
writes a value with an apostrophe and a trailing comment and silently gets
the comment folded into the value.

## Fix

Applied: `_strip_comment` now only enters quote-tracking mode when the
value is a *genuinely quoted* scalar — one that **starts** with a quote
char (`quoted = text[:1] in ('"', "'")`). In a bare value a lone quote
char (the apostrophe in `don't`, the `'` in `5 o'clock`) is treated as
ordinary content and never flips `in_q`, so the trailing `# comment` is
still recognized and stripped. A `#` inside a genuinely quoted run is
still preserved because the leading quote turns tracking on. This keeps
the change local to `_strip_comment`; `_split_key` still routes every
bare value through it unchanged.


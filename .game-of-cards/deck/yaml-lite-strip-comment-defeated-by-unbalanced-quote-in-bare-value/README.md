---
title: yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value
summary: "yaml-lite's `_strip_comment` tracks quote state to avoid stripping a `#` inside a quoted run, but on a bare (unquoted) scalar value containing a lone `'` or `\"` (e.g. an apostrophe) it enters quote mode and never exits, so a trailing `# comment` is never recognized and is kept as part of the value. Real YAML strips that comment. Confirmed: `safe_load(\"title: don't  # note\")` returns `{'title': \"don't  # note\"}`. Narrow blast radius — goc's emitter quotes values containing `#`, so it only bites hand-edited frontmatter / config.yaml / canonical-tags.md."
status: open
stage: null
contribution: low
created: "2026-05-26T22:28:42Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: a `reproduce.py` asserts `safe_load("title: don't  # note") == {"title": "don't"}` (comment stripped, matching real YAML); fails before the fix, passes after
  - [ ] TDD: regression guard — a `#` inside a properly *balanced* quoted run is still NOT stripped (e.g. `a: "x # y"` → `"x # y"`), and a bare value with no quote still strips its comment
  - [ ] PROCESS: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green (the vendored parser is mirrored into the plugin payloads)
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

The quote-tracking in `_strip_comment` is appropriate for a properly
quoted scalar but wrong for a bare value. Options to weigh in log.md:
treat quote characters as ordinary content in a bare value (only honor
`in_q` when the value actually *starts* with a quote, i.e. is a quoted
scalar), or have `_split_key` route quoted vs bare values to different
comment-stripping logic. Either way a lone apostrophe in a bare value must
not suppress comment detection, while a `#` inside a genuinely quoted run
must still be preserved.


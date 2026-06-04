---
title: strip-comment-closes-double-quoted-scalar-on-backslash-escaped-quote
status: active
stage: null
contribution: medium
created: "2026-06-04T04:34:46Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — `emit_frontmatter({'summary': 'a " b #c', ...})` round-trips through `parse_frontmatter` unchanged, and `safe_load('k: "a\\" b #c"\n')` returns `{'k': 'a" b #c'}`. Fails before the fix, passes after.
  - [ ] TDD: regression guard in tests/test_yaml_lite.py next to `test_block_key_with_escaped_quote_in_quoted_value` — a `#` inside a *balanced* double-quoted scalar that contains an escaped quote is preserved, and a bare value with an unbalanced lone quote still strips its trailing comment (`title: don't  # note` → `don't`).
  - [ ] MECHANICAL: `_strip_comment` honors backslash escapes inside double-quoted strings (skip the char after a backslash when `in_q == '"'`), mirroring `_split_flow` and `_split_key`.
  - [ ] PROCESS: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green (the vendored parser is mirrored into the plugin payloads).
worker: {who: "claude[bot]", where: main}
---

# strip-comment-closes-double-quoted-scalar-on-backslash-escaped-quote

## Summary

`yaml_lite._strip_comment` tracks quote state to avoid stripping a `#`
that sits inside a quoted scalar, but — unlike its two sibling
scanners `_split_flow` and `_split_key` — it has no backslash-escape
handling. An emitter-produced `\"` inside a double-quoted value is
misread as the *closing* quote, so a later ` #` is treated as a
comment delimiter and the value is silently truncated on read.

## Location

`goc/_vendor/yaml_lite.py:423-435` — the quote-tracking loop inside
`_strip_comment`.

## What's broken

`_strip_comment`'s loop opens and closes quote state but never skips
the character after a backslash:

```python
for i, c in enumerate(text):
    if in_q:
        if c == in_q:          # <-- closes on an ESCAPED quote too
            in_q = None
    elif flow and c in ("[", "{"):
        depth += 1
    ...
    elif (quoted or flow) and c in ('"', "'"):
        in_q = c
    elif c == "#" and depth == 0 and i > 0 and text[i - 1] in (" ", "\t"):
        return text[:i].rstrip()
return text
```

Its two siblings both guard the escape. `_split_flow`
(`yaml_lite.py:356-361`):

```python
elif in_q:
    buf.append(c)
    if c == "\\" and in_q == '"':
        escaped = True  # double-quoted YAML escapes the next char
    elif c == in_q:
        in_q = None
```

`_split_key` (`yaml_lite.py:390-394`):

```python
elif in_q:
    if c == "\\" and in_q == '"':
        escaped = True  # double-quoted YAML escapes the next char
    elif c == in_q:
        in_q = None
```

For the value `"a \" b #c"`, `_strip_comment` reaches the `\"`,
treats the `"` as the closing quote (`in_q = None`), then sees ` #`
and returns `"a \" b` — truncated. Downstream, `_parse_double_quoted`
requires a balanced trailing `"`, so the now-unterminated string is
returned verbatim as `'"a \\" b'`: both the leading quote and the
backslash leak into the value.

The closed sibling card
[yaml-lite-flow-collection-mis-splits-on-backslash-escaped-quote](../yaml-lite-flow-collection-mis-splits-on-backslash-escaped-quote/)
asserted in its DoD that the escape fix was *"already applied to
`_strip_comment`/`_parse_double_quoted`"* — but that was inaccurate.
`_strip_comment` only ever received quote-*gating* (from
[yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value](../yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value/))
and flow-*gating* (from
[yaml-lite-truncates-flow-collection-with-hash-in-quoted-element](../yaml-lite-truncates-flow-collection-with-hash-in-quoted-element/));
the backslash-escape arm was never added. It is the last of the three
hand-rolled quote scanners still missing it.

## Empirical evidence

`reproduce.py` output (before the fix):

```
[BUG] safe_load('k: "a\" b #c"')  ->  {'k': '"a\\" b'}   (expected {'k': 'a" b #c'})
[BUG] round-trip summary='a " b #c'  ->  '"a \\" b'
[BUG] round-trip summary='measure 5" #wide'  ->  'measure 5\\'
[OK ] round-trip summary='plain " quote no hash'  ->  'plain " quote no hash'
[OK ] guard safe_load("title: don't  # note")  ->  {'title': "don't"}
[OK ] guard safe_load('a: "x # y"')  ->  {'a': 'x # y'}

FAIL: _strip_comment mis-handles a backslash-escaped quote in a double-quoted scalar.
```

After the fix every line reads `[OK ]` and the script exits zero.

## Why it matters

The frontmatter emitter `_yaml_inline` (`engine.py:244-253`)
double-quotes and `\`/`"`-escapes any single-line scalar that
contains `#`, `"`, or other YAML-significant characters:

```python
escaped = s.replace("\\", "\\\\").replace('"', '\\"')
return f'"{escaped}"'
```

So any card whose `summary` (or another single-line scalar field)
contains a literal `"` followed later by ` #` is written to disk
correctly but read back corrupted on the next `load_card`. Concrete
write paths that produce such a value: `goc new --summary "..."`,
`goc quality-pass`'s LLM-authored summary rewrite, and any re-emit
during a status/decide mutation. The corruption is silent at write
time and surfaces on the next read — the round-trip invariant that
`emit_frontmatter`/`parse_frontmatter` are supposed to uphold is
broken for this input shape.

The vendored parser is mirrored into every plugin payload
(`claude-plugin/goc/`, `codex-plugin/goc/`, `openclaw-plugin/goc/`),
so the corruption ships to consumers too.

## Fix

In `_strip_comment`, add an `escaped` flag and skip the char after a
backslash inside a double-quoted run, mirroring `_split_key`:

```python
in_q: str | None = None
escaped = False
depth = 0
for i, c in enumerate(text):
    if escaped:
        escaped = False
    elif in_q:
        if c == "\\" and in_q == '"':
            escaped = True  # double-quoted YAML escapes the next char
        elif c == in_q:
            in_q = None
    elif flow and c in ("[", "{"):
        depth += 1
    elif flow and c in ("]", "}"):
        if depth > 0:
            depth -= 1
    elif (quoted or flow) and c in ('"', "'"):
        in_q = c
    elif c == "#" and depth == 0 and i > 0 and text[i - 1] in (" ", "\t"):
        return text[:i].rstrip()
return text
```

Single quotes do not use backslash escapes, so gating the escape on
`in_q == '"'` matches both siblings exactly.

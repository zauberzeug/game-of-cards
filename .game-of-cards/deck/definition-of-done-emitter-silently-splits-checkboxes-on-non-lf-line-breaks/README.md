---
title: definition-of-done-emitter-silently-splits-checkboxes-on-non-lf-line-breaks
summary: "The `definition_of_done` branch in `emit_frontmatter` (engine.py:354) routes the value unconditionally through `_emit_block_field`, which splits on `str.splitlines()` and rejoins with LF — so a DoD carrying a non-LF break (VT/FF/NEL/U+2028/U+2029) is silently split into extra lines, fabricating or destroying a `- [ ]` checkbox and changing the closure count `goc done` gates on. Every OTHER multi-line field already refuses such a break via the `_contains_line_break` guard at engine.py:368; the DoD branch is the lone exemption. Sibling of the closed inline-emitter-writes-non-newline-line-breaks-bare card, which hardened the generic branch but not this one."
status: active
stage: null
contribution: medium
created: "2026-06-25T07:41:20Z"
closed_at: null
human_gate: none
advances:
  - frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a DoD value carrying a non-LF line break either round-trips faithfully through emit_frontmatter -> parse_frontmatter or is refused with a FrontmatterError; it must NOT silently split the line.
  - [ ] TDD: a regression test in tests/ asserts the DoD branch's behaviour on a non-LF break (matching the existing summary/generic-field test posture) — round-trip or raise, never silent rewrite.
  - [ ] MECHANICAL: the DoD branch reuses the existing `_contains_line_break` predicate (single source of truth), not a fresh hand-maintained char list — consistent with the emitter quote-trigger meta-fix this card advances.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` green (the emitter is mirrored into the plugin payloads).
worker: {who: "claude[bot]", where: main}
---

# definition-of-done-emitter-silently-splits-checkboxes-on-non-lf-line-breaks

## Location

- DoD emit branch: `goc/engine.py:354-356` (`emit_frontmatter`) — routes
  unconditionally through `_emit_block_field`.
- The guard it bypasses: `goc/engine.py:365-385` (the generic multi-line
  branch) gates on `_contains_line_break(value.replace("\n", ""))`.
- Block splitter: `goc/engine.py:304` (`_emit_block_field`) — `lines = text.splitlines()`.
- Single-source predicate: `goc/engine.py:193-207` (`_contains_line_break`).
- Reachability: `goc/engine.py:3737-3762` (`_apply_dod_rewrite`).

## What's broken

`emit_frontmatter` has special-cased `definition_of_done` to always use
block style, with no line-break guard:

```python
if key == "definition_of_done":
    lines.extend(_emit_block_field(key, value or "", indicator="|"))
    continue
```

`_emit_block_field` splits the value with `str.splitlines()` and the
vendored parser reads the lines back joined with LF. `str.splitlines()`
treats nine characters beyond LF as line boundaries (CR, VT, FF, FS, GS,
RS, NEL, U+2028, U+2029). So any of those embedded in a DoD value is
silently rewritten to LF on the emit → parse round-trip.

Every *other* multi-line string field already defends against exactly
this. The generic branch only takes block style when the value carries
**no** non-LF break, and otherwise falls through to `_yaml_inline`, which
refuses:

```python
if (
    isinstance(value, str)
    and "\n" in value
    and not _contains_line_break(value.replace("\n", ""))
):
    # ... any *other* break character (CR/VT/FF/...) would be silently
    # rewritten to LF. A value carrying such a character therefore falls
    # through to `_yaml_inline` below, which refuses it at the boundary
    # rather than corrupting it here.
```

The DoD branch is the lone multi-line field exempt from that safety net.

## Empirical evidence

`reproduce.py` output on a clean checkout (defect present):

```
DEFECT PRESENT:
DoD emitter silently rewrote the non-LF break:
  authored:    '- [ ] keep this one item\x0bnot two'
  round-trip:  '- [ ] keep this one item\nnot two\n'
```

One authored checkbox item became two lines. The same vertical-tab in a
`summary` field raises `FrontmatterError` — the inconsistency is the
defect.

## Why it matters

Splitting a DoD line can fabricate or destroy a `- [ ]` / `- [x]`
checkbox boundary, which is exactly the count `count_dod_boxes` feeds the
closure gate `goc done` enforces. Corrupting that count silently
weakens or breaks the closure contract.

Reachability path: `_apply_dod_rewrite` (engine.py:3737) — the
`goc quality-pass` LLM-rewrite applier — assigns
`fm["definition_of_done"]` directly from LLM-returned `fix` text and then
calls `emit_frontmatter`. LLM output is not newline-sanitized, and
`Path.read_text()`'s universal-newline normalization collapses only
`\r` / `\r\n` — it leaves VT/FF/NEL/U+2028/U+2029 intact — so such a
character reaches the emitter unchanged. This is the same class of silent
emitter corruption fixed for the inline/generic branches in the closed
card
[inline-emitter-writes-non-newline-line-breaks-bare-dropping-subsequent-frontmatter](../inline-emitter-writes-non-newline-line-breaks-bare-dropping-subsequent-frontmatter/);
that fix hardened `_yaml_inline` and the generic block branch but did not
reach this DoD-specific branch.

## Fix

Apply the same guard the generic branch uses to the DoD branch: if the
DoD value (with LF stripped) still contains a line break, refuse via the
canonical `_yaml_inline` boundary error instead of silently splitting.
Reuse `_contains_line_break` so the dangerous-character set stays derived
from `str.splitlines()` (single source of truth), consistent with the
emitter quote-trigger meta-fix this card advances:

```python
if key == "definition_of_done":
    dod = value or ""
    if isinstance(dod, str) and _contains_line_break(dod.replace("\n", "")):
        # Block style faithfully round-trips only LF; a non-LF break would
        # be silently rewritten, corrupting the checkbox count. Refuse at
        # the boundary, matching every other multi-line field.
        _yaml_inline(dod)  # raises FrontmatterError with the shared message
    lines.extend(_emit_block_field(key, dod, indicator="|"))
    continue
```

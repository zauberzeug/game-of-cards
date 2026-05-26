---
title: frontmatter-emitter-mangles-block-scalar-values-that-carry-leading-whitespace
summary: "`_emit_block_field` prefixes every content line with a fixed 2-space indent but never accounts for the value's own leading whitespace. A block-scalar value whose first line is more-indented than the rest emits YAML that the parser REJECTS on re-parse (FrontmatterError); a value where all lines share leading indent round-trips but SILENTLY STRIPS that indent. Breaks the emit→parse round-trip the rest of the frontmatter family guarantees."
status: open
stage: null
contribution: medium
created: "2026-05-26T22:38:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a block-scalar value whose first
        line is more-indented than the rest round-trips (emit→parse)
        without raising, and a value where every line shares a leading
        indent round-trips byte-for-byte (no silent strip).
  - [ ] TDD: round-trip is preserved for the existing block-scalar
        cases too (empty lines, trailing content, multi-paragraph DoD),
        so the fix does not regress the recently-closed block-scalar
        siblings.
  - [ ] MECHANICAL: the fix lands in `goc/templates/...` source-of-truth
        (the engine is vendored), not only the consumer mirror; plugin
        mirrors re-sync and `python scripts/sync_plugin_assets.py --check`
        passes.
  - [ ] PROCESS: `uv run goc validate` is clean on this repo's own deck.
---

# Frontmatter emitter mangles block-scalar values that carry leading whitespace

## Location

`goc/engine.py:234-240` — `_emit_block_field`.

## What's broken

`_emit_block_field` renders a multi-line string with a fixed 2-space
prefix and **no explicit indentation indicator**, and it never
normalizes or accounts for the content line's *own* leading
whitespace:

```python
def _emit_block_field(key: str, value: str, *, indicator: str) -> list[str]:
    """Render a multi-line string field with literal-block style (`|` or `|-`)."""
    text = (value or "").rstrip("\n")
    out = [f"{key}: {indicator}"]
    for ln in text.splitlines():
        out.append(f"  {ln}" if ln else "")
    return out
```

When a content line carries its own leading spaces, the emitted block
is malformed in one of two ways:

1. **First line more-indented than the rest → re-parse RAISES.** The
   parser fixes `block_indent` from the inflated first line, then judges
   a later 2-space line as "less than the block indent" and raises
   `FrontmatterError`. This is the exact ambiguity the closed parser-side
   card
   [block-scalar-parser-chops-characters-when-a-later-line-is-less-indented-than-the-first](../block-scalar-parser-chops-characters-when-a-later-line-is-less-indented-than-the-first/)
   taught the parser to reject — the emitter is the side that *produces*
   such output.

2. **All lines share a leading indent → SILENT data loss.** The common
   leading whitespace is folded into the block indent and stripped on
   re-parse, so `"  - [ ] nested"` comes back as `"- [ ] nested"`.

## Empirical evidence

```
=== EMITTED A (first line carries 2 leading spaces) ===
definition_of_done: |
    indented first
  second line
=== RE-PARSE A ===
FrontmatterError: YAML parse error inside frontmatter: line 4:
block scalar content line is indented 2, less than the block indent 4
but more than its declaration 0; ambiguous indentation

=== ROUND-TRIP B (every line indented 2) ===
ORIGINAL : '  - [ ] nested\n  - [ ] second'
ROUNDTRIP: '- [ ] nested\n- [ ] second\n'
MATCH    : False
```

Run `uv run python deck/frontmatter-emitter-mangles-block-scalar-values-that-carry-leading-whitespace/reproduce.py`.

## Why it matters

The frontmatter family has shipped a long run of round-trip-correctness
fixes (trailing whitespace, float/int/bool/null quoting, empty block
scalars). This is the same contract — emit must produce text that
parses back to the original value — broken on the emitter side for
block scalars with leading whitespace. A `definition_of_done` whose
items are themselves indented (nested checklists, fenced examples,
quoted YAML) either crashes a re-read or silently loses its
indentation. Any card edited through the emit path is at risk.

## Fix

Emit an **explicit indentation indicator** so the block indent is
unambiguous regardless of content leading whitespace, e.g. `|2` /
`|2-` paired with a 2-space prefix, OR compute a base indent that
exceeds the value's own maximum leading whitespace and emit that
indicator. The parser already understands explicit indicators (see the
"declaration" term in the error above). Pick the approach that keeps
the emitted YAML readable and round-trips both failing cases; verify
against the existing block-scalar siblings so nothing regresses. **Do
NOT apply the fix here — this card is the briefing.**

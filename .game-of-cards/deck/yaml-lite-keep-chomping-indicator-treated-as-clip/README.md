---
title: yaml-lite-keep-chomping-indicator-treated-as-clip
summary: "The vendored YAML parser maps the `|+` (keep) block-scalar chomping indicator to the same behavior as bare `|` (clip — one trailing newline) instead of keeping all trailing blank lines. The goc emitter never emits `|+`, so this only affects externally-authored frontmatter; parked unverified, low impact."
status: done
stage: null
contribution: low
created: "2026-05-26T20:44:09Z"
closed_at: 2026-05-26T21:39:45Z
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: a reproduce.py parses a `|+` block scalar with trailing blank lines and asserts the result preserves them (distinct from `|` clip)
  - [x] MECHANICAL: `_resolve_value` (goc/_vendor/yaml_lite.py:184-186) and `_parse_block_scalar` distinguish keep (`|+`) from clip (`|`) and strip (`|-`) — a three-way chomp, not a boolean `strip`
  - [x] PROCESS: drop the `unverified` tag once the reproduce.py lands; or disprove if YAML 1.1/1.2 chomp semantics are deemed out-of-scope for the lite parser
worker: {who: "claude[bot]", where: main}
---

# yaml-lite treats the `|+` keep-chomping indicator as clip

> **Verified & fixed (2026-05-26).** The `reproduce.py` confirmed the defect
> but with the symptom *inverted* from this card's inspection: `|+` (keep) was
> already correct, while **both `|` (clip) and `|-` (strip) wrongly retained
> trailing blank lines** they are supposed to chomp. The root cause and fix are
> exactly as scoped — a real three-way chomp instead of a clip-vs-strip boolean.
> See the `log.md` closure entry.

## Location

`goc/_vendor/yaml_lite.py:184-186` — `_resolve_value`:

```python
if rest in ("|", "|-", "|+"):
    strip = rest == "|-"
    return self._parse_block_scalar(parent_indent, strip)
```

and `goc/_vendor/yaml_lite.py:146,177-178` — `_parse_block_scalar`:

```python
def _parse_block_scalar(self, declaration_indent: int, strip: bool) -> str:
    ...
    text = "\n".join(chunks)
    return text if strip else text + "\n"
```

## Hypothesis

YAML defines three chomping indicators: clip (bare `|`, keep one trailing
newline), strip (`|-`, no trailing newline), and keep (`|+`, preserve **all**
trailing blank lines). The parser collapses this to a single boolean `strip`:
`|-` -> `strip=True`, everything else -> `strip=False`. So `|+` is parsed
identically to bare `|` — it appends exactly one `\n` and drops any trailing
blank lines that the `|+` keep indicator is specifically meant to retain.

## Why deferred

The goc emitter (`_emit_block_field`, goc/engine.py:206-212) only ever emits `|`
or `|-`; it never emits `|+`. So a round-trip through goc's own write path never
exercises this branch. The discrepancy only surfaces for frontmatter authored
by hand or by an external tool that uses `|+`. Low impact, hence `unverified`
and `contribution: low`.

## Falsification recipe

1. Parse `x: |+\n  a\n\n\n` (a `|+` block with two trailing blank lines).
2. Compare to a YAML 1.1/1.2 reference parser: keep should yield `"a\n\n\n"`.
3. If yaml_lite returns `"a\n"` (one newline, blanks dropped), the hypothesis
   holds. If it already preserves the blanks, disprove. Also legitimate to
   **disprove** on scope grounds if the lite parser explicitly declares chomp
   fidelity out of scope (document that decision in the closed card).

Surfaced by the audit hunter alongside
[frontmatter-emitter-does-not-quote-integer-looking-string-scalars](../frontmatter-emitter-does-not-quote-integer-looking-string-scalars/).

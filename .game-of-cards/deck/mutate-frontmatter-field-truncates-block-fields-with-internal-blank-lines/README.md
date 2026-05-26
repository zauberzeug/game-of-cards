---
title: mutate-frontmatter-field-truncates-block-fields-with-internal-blank-lines
summary: "The line-anchored regex in `mutate_frontmatter_field` matches block continuation lines with `(?:\\n[ \\t]+[^\\n]*)*`, which stops at the first internal blank line. Mutating a block-scalar/block-list field that contains a blank line would orphan everything after the blank. Latent today — no current caller mutates a block field — so parked unverified."
status: open
stage: null
contribution: low
created: "2026-05-26T20:44:09Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py mutates a `definition_of_done` block that contains an internal blank line and asserts the post-mutation frontmatter is intact (no orphaned tail)
  - [ ] MECHANICAL: the continuation pattern in goc/engine.py:282-283 captures blank lines that belong to the block (e.g. `(?:\n(?:[ \t]+[^\n]*)?)*` anchored to stop at the next `key:` line) without swallowing the rest of the frontmatter
  - [ ] PROCESS: drop the `unverified` tag once the reproduce.py lands and shows the defect firing
---

# `mutate_frontmatter_field` truncates block fields with internal blank lines

> **Unverified.** Confirmed by code inspection; no `reproduce.py` budget this
> round, and the defect is latent (no current caller mutates a block field).
> Parked so the observation is not lost.

## Location

`goc/engine.py:282-285` — `mutate_frontmatter_field`:

```python
pattern = re.compile(
    rf"^{re.escape(field_name)}:[ \t]*[^\n]*(?:\n[ \t]+[^\n]*)*",
    re.MULTILINE,
)
```

## Hypothesis

The continuation group `(?:\n[ \t]+[^\n]*)*` matches a newline followed by **at
least one** whitespace char and then content. An internal blank line in a block
field is `\n` with nothing after it — it does not match `[ \t]+[^\n]*`, so the
match stops there. `pattern.sub(..., count=1)` then replaces only the captured
prefix, and the orphaned tail (everything after the blank line) is left dangling
in the frontmatter — almost certainly producing invalid YAML or a mis-parsed
card on the next load.

`_emit_block_field` (goc/engine.py:206-212) emits empty source lines as truly
empty lines (`out.append(f"  {ln}" if ln else "")`), so a `definition_of_done`
that contains a blank line round-trips a real blank line into the frontmatter —
the exact shape that would trip this regex.

## Why deferred

`mutate_frontmatter_field` is currently only invoked for **flat** fields
(`worker`, `status`, `closed_at`); no live code path mutates a multi-line block
field. So the bug cannot fire today. It is a latent trap for any future verb
that edits a block field in place (e.g. an eventual `goc edit-dod`).

## Falsification recipe

1. Build a frontmatter string whose `definition_of_done:` block has an internal
   blank line (`- [ ] a\n\n  - [ ] b`).
2. Call `mutate_frontmatter_field(text, "definition_of_done", "| ...")` — or any
   value — and re-parse the result.
3. If the tail (`- [ ] b` and any fields below the DoD) survives intact, the
   hypothesis is **wrong** (disprove). If the tail is orphaned / the card no
   longer parses, the hypothesis holds.

Surfaced by the audit hunter alongside
[frontmatter-emitter-does-not-quote-integer-looking-string-scalars](../frontmatter-emitter-does-not-quote-integer-looking-string-scalars/).

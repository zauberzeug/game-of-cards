---
title: block-scalar-parser-collapses-whitespace-only-content-lines
summary: "The vendored yaml-lite block-scalar parser tests each content line for blankness with `raw.rstrip() == \"\"` and, when true, appends an empty string — collapsing a whitespace-only content line (indent + interior spaces) to nothing. The goc frontmatter emitter writes such a line verbatim, so a multiline `summary`/`definition_of_done` value with an all-whitespace interior line does NOT survive emit->parse. This is the residual whitespace-only-line code path left unfixed by the closed sibling `block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip`, which only fixed the non-blank content-line slice."
status: done
stage: null
contribution: medium
created: "2026-05-26T22:21:44Z"
closed_at: "2026-05-26T22:47:29Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero (the whitespace-only content line round-trips losslessly)
  - [x] TDD: a block scalar whose only content is a single whitespace-only line still round-trips (e.g. value `"   "` survives emit->parse), and an all-blank/whitespace tail is still clip/strip-chomped exactly as before (no regression in trailing-blank-line handling)
  - [x] MECHANICAL: the fix preserves the existing whitespace-only-line semantics outside a block (the `rstripped == ""` short-circuit at `goc/_vendor/yaml_lite.py:164` is corrected, not removed wholesale, so genuinely-empty lines past the block indent still chomp correctly)
  - [x] PROCESS: `uv run goc validate` clean and `python scripts/sync_plugin_assets.py --check` green (the vendored parser is mirrored into the plugin payloads)
---

title: x
summary: |-
  first line
     
  third line
status: open
contribution: medium
human_gate: none
tags: [bug]
advances: []
advanced_by: []
---

=== round-trip of summary ===
in : 'first line\n   \nthird line'
out: 'first line\n   \nthird line'
match: True

OK: block-scalar round-trip is lossless.
```

Exit code 0 after the fix (the whitespace-only content line round-trips).

## Why it matters

`goc` rewrites frontmatter on most mutating verbs (`status`, `decide`,
`advance`, `wait`, `quality-pass`, `move`). A card whose `summary` or
`definition_of_done` contains a whitespace-only interior line — a real
shape in Markdown, where a line of spaces between paragraphs or inside a
fenced/indented block is content — is silently de-whitespaced the next time
any such verb touches the card. The emit/parse contract the trailing-
whitespace fix was meant to guarantee ("a value goc emits survives being
parsed back by goc") is still broken for this input class.

## Fix

Distinguish "a line that is blank because it has no characters past the
block indent" from "a line whose characters past the block indent are
whitespace". Once `block_indent` is established, a line should only be
treated as a structural blank when it has nothing at or beyond the block
indent; otherwise it is a content line and must be sliced `raw[block_indent:]`
like any other.

A minimal shape: keep the `rstripped == ""` short-circuit only while
`block_indent is None` (leading blank lines before the first content line,
where there is no indent to slice against yet). After `block_indent` is set,
fold whitespace-only lines into the normal content path — slice
`raw[block_indent:]` (which yields the meaningful interior spaces, or `""`
for a truly-short line) and let the existing trailing-blank-line chomp at
lines 202-206 drop genuine trailing blanks. Care is needed so a line shorter
than `block_indent` (fewer characters than the indent) still yields `""`
rather than raising or eating the next key.


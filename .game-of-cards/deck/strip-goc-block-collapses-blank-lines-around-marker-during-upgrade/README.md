---
title: strip-goc-block-collapses-blank-lines-around-marker-during-upgrade
summary: "UNVERIFIED. `_strip_goc_block` removes a GoC marker block from AGENTS.md/CLAUDE.md by replacing the block plus its surrounding `\\n*` runs with a single `\\n`. When user-authored content sits both above and below the block, the blank-line separator between them is collapsed — a paragraph above and a `## Section` below get jammed onto adjacent lines. Content is preserved but paragraph/heading separation is destroyed during upgrade migration."
status: active
stage: null
contribution: medium
created: "2026-05-27T07:40:12Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py feeds `_strip_goc_block` a file with user content above AND below the marker block and asserts the blank-line separator survives; fails on current code, passes after the fix. Promote off `unverified` when it lands.
  - [ ] MECHANICAL: `_strip_goc_block` preserves the inter-paragraph blank line (e.g. replace the block with `\n\n` when content exists on both sides, or strip the block without eating both surrounding blank runs).
worker: {who: "claude[bot]", where: main}
---

# `_strip_goc_block` collapses the blank line around the marker block

**UNVERIFIED** — code-read confirmed; agent reports a live scratch repro,
not yet captured into a committed reproduce.py here.

## Hypothesis (file:line)

`goc/install.py:168-169`:

```python
pattern = re.compile(rf"\n*{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n*", re.DOTALL)
new = pattern.sub("\n", text).strip()
```

The leading and trailing `\n*` greedily consume the blank lines on *both*
sides of the marker block, and the replacement is a single `\n`. So when a
user paragraph sits above the block and a user `## Section` sits below it,
the two are rejoined with one newline — the blank line that separated a
paragraph from the next heading is destroyed. The block content itself is
correctly removed and surrounding text is preserved; only the structural
blank-line separator is lost.

## Why deferred

No reproduce.py captured in this card yet — the audit agent reported a
live scratch reproduction but did not commit one. The fix direction is
clear (replace with `\n\n` when content exists on both sides, or trim only
one blank run per side), but it needs a committed failing test first.

## Falsification recipe

Feed `_strip_goc_block` a temp file containing:

```
Intro paragraph.

<!-- BEGIN GOC v1.2.3 -->
body
<!-- END GOC -->

## My Section
```

Expected after strip: `Intro paragraph.\n\n## My Section` (blank line
preserved). Actual (hypothesis): `Intro paragraph.\n## My Section` (blank
line collapsed).

## Surfaced by

audit-deck static hunt (general-purpose agent, install.py / sync seam),
2026-05-27.

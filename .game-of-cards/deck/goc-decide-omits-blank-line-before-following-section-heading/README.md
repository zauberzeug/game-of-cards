---
title: goc-decide-omits-blank-line-before-following-section-heading
summary: |-
  When `goc decide` replaces an existing `## Decision required` section with `## Decision`, the new block ends in a single `
  ` while the regex's positive lookahead leaves the next `## ` heading attached on the very next line. Markdown emerges malformed: `*Reasoning:* X` runs straight into `## NextSection`.
status: done
stage: null
contribution: medium
created: "2026-05-29T07:36:02Z"
closed_at: "2026-05-29T07:42:12Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a unit test for `replace_or_append_decision` covering the "Decision required followed by another `## ` section" case asserts a blank line between `*Reasoning:* X` and the next heading.
  - [x] TDD: an end-to-end test runs `goc decide` on a card whose body contains `## Decision required` followed by `## Notes`, then re-reads the file and asserts the resulting markdown round-trips through a basic renderer with the headings separated.
  - [x] MECHANICAL: `replace_or_append_decision` in `goc/engine.py` emits a trailing blank line so the next `## ` heading is properly separated; the append branch remains clean (no double-blank).
  - [x] MECHANICAL: existing tests pass (`uv run python -m unittest discover -s tests`); plugin mirrors are re-synced.
worker: {who: "claude[bot]", where: main}
---

# `goc decide` glues the new Decision block to the next section heading

## Location

`goc/engine.py:351-368` — the `DECISION_REQUIRED_RE` regex and the
`replace_or_append_decision` helper used by `goc decide`.

## What's broken

```python
351  DECISION_REQUIRED_RE = re.compile(
352      r"^## Decision required[^\n]*\n(.*?)(?=^## |\Z)",
353      re.MULTILINE | re.DOTALL,
354  )
...
363  def replace_or_append_decision(body: str, decision: str, reasoning: str, today: str) -> str:
364      """Replace `## Decision required` with `## Decision`, or append a new section."""
365      block = f"## Decision\n\n*Resolved {today}:* {decision}\n\n*Reasoning:* {reasoning}\n"
366      if DECISION_REQUIRED_RE.search(body):
367          return DECISION_REQUIRED_RE.sub(lambda _: block, body, count=1)
368      return body.rstrip("\n") + "\n\n" + block
```

The regex consumes `## Decision required\n<content>` non-greedily up to the
position just before the next `## ` heading (positive lookahead — does NOT
consume it). The replacement `block` ends in a single `\n`. The blank line
that previously separated `## Decision required`'s content from the next
section was part of `<content>` (consumed by `.*?`), so the substitution
loses it. The new `*Reasoning:* X\n` is immediately followed by the next
`## ` heading on the very next line — malformed Markdown.

The append branch on line 368 is correct: it prefixes `"\n\n"` to the new
block. Only the *replace* branch is broken.

## Empirical evidence

```python
>>> from goc.engine import replace_or_append_decision
>>> body = "Pre-content here.\n\n## Decision required\n\nWhat should we do?\n\n## Notes\n\nSome appendix material.\n"
>>> print(replace_or_append_decision(body, "Pick A", "Simpler", "2026-05-29"))
Pre-content here.

## Decision

*Resolved 2026-05-29:* Pick A

*Reasoning:* Simpler
## Notes

Some appendix material.
```

Note `*Reasoning:* Simpler\n## Notes` — no blank line between them. CommonMark
allows this in most parsers but it is sloppy output (the GoC convention
elsewhere always separates headings with a blank line; the append branch
preserves that contract).

## Reachability path

`Skill(decide-card)` is the documented happy path; users run `goc decide
<title> --decision "X" --because "Y"` to resolve parked cards. The bug
fires whenever the decided card carries any section *after* the
`## Decision required` block. Real cards in this repo's own deck that
match the shape today (found via `awk` scan of `## Decision required`
followed by a later `## ` line):

- `.game-of-cards/deck/audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings/README.md`
- `.game-of-cards/deck/goc-wait-does-not-clear-stale-elapsed-waiting-until/README.md`
- `.game-of-cards/deck/heaviest-skills-re-load-full-methodology-briefing-per-card-cycle/README.md`
- `.game-of-cards/deck/provide-openclaw-plugin-for-skills-and-hooks/README.md`

Any of these decided via `goc decide` today would emerge with the malformed
join.

## Why it matters

The README is the user-facing dashboard, and `goc decide` is the one-action
handoff humans use to unblock parked cards (the lowering action that
`pull-card` resumes from). When the post-decision README has its sections
visually fused — `*Reasoning:* X` running into `## NextHeading` — the card
looks rough, and stricter Markdown renderers (especially GitHub's, which is
the primary read surface) may collapse the heading-recognition rules in
unhelpful ways. `goc validate` does not body-lint, so the drift is silent.

## Fix

Change the `block` template in `replace_or_append_decision` so the trailing
newline matches what the consumed content used to provide. One option:

```python
block = f"## Decision\n\n*Resolved {today}:* {decision}\n\n*Reasoning:* {reasoning}\n\n"
```

The replace branch then yields `*Reasoning:* X\n\n## NextSection`; the
append branch (which already prefixes `"\n\n"` to the block) would yield a
single trailing blank line at end of file, which is harmless and matches
the prevailing trailing-newline convention.

Add a focused unit test on `replace_or_append_decision` covering both
branches (append + replace-with-next-section + replace-as-last-section)
to lock the contract.

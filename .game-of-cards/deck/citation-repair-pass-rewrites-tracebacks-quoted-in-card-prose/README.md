---
title: citation-repair-pass-rewrites-tracebacks-quoted-in-card-prose
summary: "The refine-deck citation scope rule puts a quoted error or transcript out of scope but gives a mechanical record test only for fenced blocks, so a cite in prose reads as an assertion about current code. A traceback frame quoted in prose on repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field was renumbered by all four passes that ran after the rule shipped, until the 2026-11-16 pass restored it by hand; the 2026-11-23 pass's classifier proposed it again and only a manual read held it. Records belong in fences, where the existing marker test already protects them."
status: active
stage: null
contribution: low
created: "2026-11-23T02:09:59Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — no live card quotes a traceback or frame chain outside a fenced block.
  - [ ] MECHANICAL: the dry-run and `--apply` result bullets on `repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field` move into a fenced block with their numbers as filed (`4954 → 4911`), so the existing marker test reads the frame as a record.
  - [ ] MECHANICAL: the scope paragraph in `goc/templates/skills/refine-deck/SKILL.md` § "Defunct file:line citations", and `reference.md` § "Citation anchor check" with it, say that a record quoted in prose is still a record, and that the pass moves it into a fence with its numbers unchanged, so the next pass's marker test protects it without a re-read.
  - [ ] MECHANICAL: `goc/templates/skills/create-card/SKILL.md` Step 5 says pasted output (reproduce.py output, tracebacks, error text) goes in a fenced block, so new records are born where the test can see them.
  - [ ] TDD: `tests/test_refine_deck_citation_anchor.py` classifies the shipped scope prose for the prose-record rule beside `documented_fenced_scope`, failing on today's text and passing after the edit.
  - [ ] MECHANICAL: mirrors regenerate — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---

# The citation repair pass rewrites tracebacks quoted in card prose

## Location

- `goc/templates/skills/refine-deck/SKILL.md:143-150` — the scope rule of
  § "Defunct file:line citations"; `reference.md` § "Citation anchor check",
  paragraph "Scope: what the cite claims, not where it sits", is its long form.
- `goc/templates/skills/create-card/SKILL.md:159` — Step 5's "Empirical
  evidence" line, which says what goes into a card but not that pasted
  output belongs in a fence.
- The instance: line 103 of
  [repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field](../repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field/).

## What's broken

The scope rule names three kinds of dated record and gives a test for only
one place a record can sit:

```text
Scope by what the cite CLAIMS, not by where it sits. A cite asserting
where code lives NOW is in scope in prose and inside a fenced block
alike — the fenced form is a COMMENT LABEL, a `#` or `//` marker before
the cite on its line. A cite that is part of a dated record — pasted
`grep -n` output (`path:line:content`), a `reproduce.py` transcript, a
quoted error — is OUT of scope: rewriting its number fabricates output
the command never produced. Repair the labels; leave the records and
report their count apart from the declines below. Undecidable → record.
```

Inside a fence the marker test decides: no `#` or `//` before the cite
means a record. Outside a fence the only test is the first sentence, which
calls a prose cite an assertion about where code lives now. "Undecidable →
record" helps only a pass that notices the line is undecidable. A quoted
result line written as a prose bullet does not look undecidable:

```text
- `goc repair-edges` (dry run) → traceback ending `ValueError: advanced_by: not a list` at `engine.py:4954 → 4911`.
- `goc repair-edges --apply` → same traceback via `_cmd_repair_edges → _mutate_pair → 4911`.
```

The first frame of that chain, line 4954 of `engine.py`, is what the card's
author saw printed on 2026-06-23 — a record. To the rule's test it is a
backticked prose cite like any other. Its anchor is a real, unique line, so every guard in
the recipe passes and the pass moves it. The second frame, `4911`, has no
path in front of it, so no pass ever touched it: the card has quoted a frame
chain that no traceback could print since 2026-08-10.

## Empirical evidence

`uv run python .game-of-cards/deck/citation-repair-pass-rewrites-tracebacks-quoted-in-card-prose/reproduce.py`,
on 2026-11-23:

```text
Live cards scanned: 193
Cites inside a quoted traceback or frame chain, in prose (outside fences and blockquotes): 1
  repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field L103: engine.py:4954
      - `goc repair-edges` (dry run) → traceback ending `ValueError: advanced_by: not a list` at `engine.py:4954 → 4

History of the frame quoted on repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field
(first number of `engine.py:N → M`; scope rule = eae2bea9):
  1368bb56 2026-06-23   4954 → 4911  as filed
  69e1e4f2 2026-08-10   5891 → 4911  rewritten before the scope rule
  f290f5f7 2026-08-17   6139 → 4911  rewritten before the scope rule
  e8449764 2026-08-24   6250 → 4911  rewritten before the scope rule
  9bad9881 2026-08-31   6300 → 4911  rewritten before the scope rule
  9d5bd88f 2026-09-07   6303 → 4911  rewritten AFTER the scope rule shipped
  278ff831 2026-09-14   6304 → 4911  rewritten AFTER the scope rule shipped
  9085ef04 2026-09-21   6356 → 4911  rewritten AFTER the scope rule shipped
  3ebd9b7e 2026-11-09   7165 → 4911  rewritten AFTER the scope rule shipped
  2a665b45 2026-11-16   4954 → 4911  restored to the filed number by hand
Rewrites after the rule shipped: 4

DEFECT PRESENT: a record quoted in prose is indistinguishable from a cite about current code under the scope rule's only test, so the next pass that does not read the line rewrites it.
```

Every pass that ran after the rule shipped rewrote the frame, four in a row.
The 2026-11-09 sweep that restored four fenced transcripts checked fenced
records only and missed it. The 2026-11-16 pass restored it by reading the
line. On 2026-11-23 the next pass's classifier, which implements the marker
test, proposed `4954 → 5074` in both its first round and its committed
re-run. Only a manual read held it. `5074` is a line in `_cmd_default`, which
`goc repair-edges` never reaches.

It is the only such line on the deck today: the reproducer's scan over 193
live cards finds one.

## Why it matters

A rewritten record is worse than a stale cite. A stale cite costs a reader
one lookup. A rewritten traceback frame claims the command printed something
it never printed, and a reader who re-runs the command to compare sees a
mismatch that looks like a behaviour change. The scope rule was written to
prevent exactly that
([citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks](../citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks/),
closed 2026-09-01). It holds wherever its test reaches and fails silently
where it does not. Recognition currently has to happen on every pass, and four
consecutive passes did not do it.

## Fix

Make prose records reachable by the test that already works, rather than
adding a second test:

1. Move the two result bullets on the instance card into a fenced block,
   numbers as filed. The marker test then reads the frame as a record on
   every later pass without anyone re-reading it.
2. In the scope paragraph (SKILL.md and reference.md), add the prose case: a
   record quoted in prose — a traceback frame, an error location, a line a
   command printed — is a record, and the pass that recognises one moves it
   into a fence with its numbers unchanged. Recognition then happens once per
   record, not once per pass.
3. In `Skill(create-card)` Step 5, say that pasted output goes in a fenced
   block, so new records start where the test reaches them.
4. Pin the new sentence with a classifier in
   `tests/test_refine_deck_citation_anchor.py`, the way
   `documented_fenced_scope` pins the fenced rule.

Rejected: a keyword test for prose (`traceback`, `→`, "printed"). It would
catch this line and nothing proves it catches the next one, and it would
leave the classification a per-pass judgment. The fence is already the one
marker every pass applies mechanically.


---
title: refine-deck-decline-count-test-fails-when-the-prose-is-only-rewrapped
summary: "Two reads in ResidueAccountingTest (tests/test_refine_deck_citation_anchor.py) find the refine-deck decline count and decline list with regexes holding literal single spaces, so moving one line break inside 'declines split six ways' or '— are REPORTED' fails the guard with a false diagnosis: that SKILL.md 'no longer lists what the citation recipe declines'. The same file ships _flat precisely so its rules survive rewrapping; these two reads skip it. Harmless while nobody rewraps, but the SKILL.md body sits 2 bytes under its size cap, so the next edit to that paragraph will be a rewrap."
status: done
stage: null
contribution: low
created: "2026-09-25T04:51:36Z"
closed_at: "2026-09-25T04:55:18Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, test]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — `ResidueAccountingTest` passes over
        copies of SKILL.md and reference.md in which one space inside
        "declines split N ways" or "— are REPORTED" has become a line break,
        as it does over the shipped files.
  - [x] TDD: `tests/test_refine_deck_citation_anchor.py` gains a test that
        runs both decline-accounting reads over the citation sections with
        every space of the two carrying paragraphs turned into a line break,
        and asserts they return what they return on the shipped text; it
        fails against the whitespace-literal reads.
  - [x] MECHANICAL: both reads go through `_flat`, the file's existing
        rewrap-proof normalizer, rather than a second one.
worker: {who: "claude[bot]", where: main}
---

# The refine-deck decline-count test fails when the prose is only rewrapped

## Location

- `tests/test_refine_deck_citation_anchor.py:1497` —
  `ResidueAccountingTest.test_reference_counts_its_own_residue_rows`.
- `tests/test_refine_deck_citation_anchor.py:1510` —
  `ResidueAccountingTest.test_core_skill_names_every_decline_the_table_carries`.

## What was broken

Both reads matched a phrase that runs through hard-wrapped markdown with a
regex that spells the spaces literally:

```python
        match = re.search(
            r"declines split (\w+) ways", reference_anchor_section()
        )
```

```python
        match = re.search(
            r"Cites the recipe declines \u2014 (.+?) \u2014 are REPORTED",
            skill_citation_section(),
            re.S,
        )
```

A line break is whitespace to every reader of that markdown, and to the
agent following it, but not to `" "`. The file already says which reading is
right, in the helper nearly every other classifier in it goes through:

```python
def _flat(prose: str) -> str:
    """Hard-wrapped prose as one lowercase line, so rules survive rewrapping."""
```

These two reads predated that convention or skipped it. On a rewrap they
returned `None`, and each test then reported the prose as gone — "SKILL.md
no longer lists what the citation recipe declines" — when it was present
word for word. The guard held only by accident of the current fill column.

## Empirical evidence

Hit while closing
[citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits](../citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits/):
adding a sixth name to the decline list pushed "are" to the next line, and
the second test failed until the paragraph was rewrapped by hand to put
"— are REPORTED" back on one line. `reproduce.py` generalizes that:

```
shipped files (control)
    words unchanged: True
    ResidueAccountingTest: ok
reference.md: 'declines split six\nways'
    words unchanged: True
    ResidueAccountingTest: FAIL
      test_reference_counts_its_own_residue_rows: AssertionError: unexpectedly None : refine-deck reference.md § Citation anchor check no longer says how many ways the declines split
SKILL.md: '—\nare REPORTED'
    words unchanged: True
    ResidueAccountingTest: FAIL
      test_core_skill_names_every_decline_the_table_carries: AssertionError: unexpectedly None : refine-deck SKILL.md no longer lists what the citation recipe declines

rewraps the guard rejects: 2 of 2
```

## Why it matters

A guard that fails on whitespace is a guard people learn to appease, not to
read: the cheapest response to its message is to shuffle line breaks until it
goes green, which teaches nothing and costs a round trip. And it is about to
fire again. `goc/templates/skills/refine-deck/SKILL.md` is 14,198 bytes
against its 14,200 cap (`tests/test_skill_body_size.py`), so any further edit
to the citation step has to trim or reflow the surrounding prose, and the
decline-list sentence is the paragraph such edits grow.

## Fix

Both reads now go through `_flat`, their patterns lowercased to match, and
live in two module-level helpers beside the file's other `documented_*`
classifiers — `documented_decline_count` (`tests/test_refine_deck_citation_anchor.py:544`)
and `documented_decline_names` (`:554`) — so the tests share one read
instead of restating the regex. Two tests guard them:
`test_both_reads_survive_a_rewrap` (`:1527`) turns every space of the two
carrying paragraphs into a line break and asserts both reads return what
they return on the shipped text (against the old reads it fails,
`'six' != None`), and `test_reads_report_what_the_prose_says` (`:1555`)
proves the reads return what the prose says rather than a fixed answer.
`reproduce.py` now reports `rewraps the guard rejects: 0 of 2`.

## Out of scope

The section-extraction regexes in the same file (`^### Defunct file:line
citations$`, `^1\. Resolve the path `, …) anchor on headings and list markers
on purpose: those ARE line-structured, and a heading that moved is a real
change. The residue table is line-structured too, and `residue_rows()` reads
it by line, correctly.

---
title: verbose-table-renders-a-multi-line-summary-raw-breaking-the-per-card-block
summary: "goc -v prints a card's summary with a bare f-string, so a multi-line summary's continuation lines carry none of the four-space indent every other entry in the per-card detail block uses and read as new records. 43 of 757 cards in this deck have one. The sibling branch in _cmd_triage already clips a multi-line summary to its first line with a see-goc-show pointer; the table renderer's own -vv DoD dump already re-indents every line."
status: done
stage: null
contribution: medium
created: "2026-09-14T05:39:04Z"
closed_at: "2026-09-14T05:45:38Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits 1 against the current engine and 0 after the fix.
  - [x] TDD: a regression test asserts that `render_table(..., verbose=1)` on a card with a multi-line `summary` emits exactly one `summary:` line and that every non-blank detail line starts with the four-space block indent.
  - [x] TDD: the same test asserts a single-line summary renders byte-identically to today (no spurious clip indicator), and that the clipped form names the card so a reader can reach the full text.
  - [x] MECHANICAL: the clip matches the sibling convention already in `_cmd_triage` — first line, then an ellipsis and a `goc show <title>` pointer — rather than inventing a third preview style.
  - [x] MECHANICAL: `uv run python -m unittest discover -s tests` passes; `uv run goc validate` passes; `python scripts/sync_plugin_assets.py --check` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc -v` renders a multi-line summary raw, breaking the per-card block

## Location

- `goc/engine.py:3367-3368` — the offending render:

  ```python
  if t.summary:
      out_lines.append(f"    summary: {t.summary}")
  ```

- `goc/engine.py:3394-3402` — the SAME function, twenty-six lines below, at
  `verbose >= 2`, re-indenting a multi-line field line by line:

  ```python
  for line in dod.splitlines():
      out_lines.append(f"    {line.rstrip()}")
  ```

- `goc/engine.py:6950-6957` — `_cmd_triage`'s summary branch, which already
  treats a multi-line summary as a clip:

  ```python
  summary_lines = entry["summary"].splitlines()
  first_line = summary_lines[0] if summary_lines else ""
  clipped = len(summary_lines) > 1 or len(first_line) > 140
  first = first_line[:140].rstrip()
  if clipped:
      lines.append(f"  > {first} … (see `goc show {entry['title']}`)")
  ```

## What's broken

`render_table`'s `verbose >= 1` block is a fixed-indent key/value list under
each data row — `why:`, `summary:`, the waiting overlay, `awaiting:`,
`worker:`, each written as `f"    {...}"`. Four spaces is what tells a reader
(and a downstream parser) that a line belongs to the row above rather than
being a new record.

Interpolating `t.summary` into that f-string only indents the FIRST line. A
summary that YAML kept as a block scalar emits its remaining lines at column
zero, where they are indistinguishable from a title row. Three surfaces in
this same file already know that: the `-vv` DoD dump re-indents every line,
and both `_cmd_triage` branches either clip to the first line or prefix every
line with `  > `. The `-v` summary line is the one that does not.

## Empirical evidence

`uv run python .game-of-cards/deck/verbose-table-renders-a-multi-line-summary-raw-breaking-the-per-card-block/reproduce.py`:

```
single-line summary: 0 unindented detail line(s)
--- rendered ---
TITLE                    STATUS  STAGE  CONTR.  VALUE  GATE  CREATED  TAGS  DOD
-----------------------  ------  -----  ------  -----  ----  -------  ----  ---
multi-line-summary-card  open    -      medium    3.0  none                 0/1
    summary: First line of the summary.
Second line that YAML kept as a block scalar.
Third line.
--- /rendered ---
UNINDENTED: 'Second line that YAML kept as a block scalar.'
UNINDENTED: 'Third line.'
DEFECT PRESENT: 2 continuation line(s) escape the block indent
```

The same corruption on the real deck, from `uv run goc --status active -v`:

```
pattern-check-hook-binary-misses-connect-to-existing-root       active  -  medium  3.0  session  ...
    summary: The Stop-hook `pattern_generalization_check.py` REMINDER offers a BINARY: "file a generalization
card" OR "no generalization needed". It has no branch for the common mature-deck case — the
pattern IS general but a root/generalization card ALREADY exists — so the right move is to CONNECT
the instance (cross-reference or an `advances` edge), not file a duplicate. As written, the hook
...
    worker: claude[bot] @ main
```

## Reachability

A multi-line `summary` is a first-class, engine-produced shape, not a
hand-editing accident:

- `emit_frontmatter` writes any multi-line string field as a block scalar,
  choosing `|`, `|-` or `|+` from the value's trailing-newline state
  (`goc/engine.py`, `emit_frontmatter` docstring), and the round-trip is
  exercised by the emitter test suite.
- `_apply_summary_rewrite` (`goc/engine.py:4615`) exists specifically so that
  "a multi-line LLM-authored summary emits as a `|-` block scalar" — i.e.
  `goc quality-pass` accepting an LLM rewrite is a supported writer of this
  shape.
- Measured on this deck: **43 of 757 cards** carry a multi-line `summary`
  today, including four of the six currently-active cards.

## Why it matters

`goc -v` is not only a human view. The `pull-card`, `scan-deck` and `standup`
skill bodies embed its output verbatim in `!`-executed context blocks, so the
unindented continuation lines land in an agent's context looking like deck
rows. An agent reading that block cannot tell prose from a record. Distinct
from [`skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json`](../skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json/),
which is about the block being cut off; here the block is complete and
structurally wrong.

## Fix

At `goc/engine.py:3367-3368`, clip to the first line and advertise the clip,
matching `_cmd_triage`'s sibling branch:

```python
if t.summary:
    summary_lines = t.summary.splitlines()
    first = (summary_lines[0] if summary_lines else "").rstrip()
    if len(summary_lines) > 1:
        first = f"{first} … (see `goc show {t.title}`)"
    out_lines.append(f"    summary: {first}")
```

Clip rather than re-indent: the `-v` help text promises a "summary line"
(singular) and every other entry in this block is one line, so re-indenting
would make one field unbounded in a fixed-height record. The closed card
[`triage-summary-fallback-preview-truncates-at-140-chars-without-indicator`](../triage-summary-fallback-preview-truncates-at-140-chars-without-indicator/)
already settled the "clip must be advertised, with a `goc show` pointer"
convention for the summary surface; this applies it to the one summary
surface that was missed. No 140-character cap is added here — the table
prints long single-line summaries in full today and that is out of scope.

## Sibling sweep

Every other summary-shaped render surface was checked and is already
multi-line-safe: `_cmd_triage`'s `decision_required` preview (prefixes every
line), `_cmd_triage`'s summary fallback (clips), `render_table` at
`verbose >= 2` (re-indents), and the JSON dumps (escaped by the encoder).
This is the only site.

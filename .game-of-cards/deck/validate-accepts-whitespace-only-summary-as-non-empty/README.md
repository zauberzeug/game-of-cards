---
title: validate-accepts-whitespace-only-summary-as-non-empty
summary: "`goc validate` accepts `summary: \"   \"` (whitespace-only) and `summary: \"\"` (empty), while `goc quality-pass` already treats both as a Missing-summary quality issue (via `(c.summary or \"\").strip()` at `engine.py:3198`). The two surfaces disagree about what counts as a present summary. Mirror the worker validation fix shape into `summary`."
status: active
stage: null
contribution: medium
created: "2026-05-30T13:24:18Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: regression test rejects `summary: "   "` and `summary: ""` with a message of shape `<title>: summary: must not be empty or whitespace-only`, mirroring the worker test in `tests/test_validate_worker_whitespace.py`
  - [ ] TDD: regression test confirms a normal `summary: "real text"` still passes
  - [ ] TDD: `reproduce.py` exits non-zero (defect no longer fires)
  - [ ] MECHANICAL: `validate_card` in `goc/engine.py` rejects whitespace-only and empty `summary` (mirrors the worker block at `engine.py:1259-1276`)
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` passes
worker: {who: "claude[bot]", where: main}
---

# validate accepts whitespace-only summary as non-empty

## Location

`goc/engine.py` — `validate_card` (around `engine.py:1201`-`engine.py:1307`).
The function validates type, enum membership, ISO-date format, and the
`worker` field's whitespace, but does not validate the **content** of
`summary` at all.

## What's broken

`validate_card` checks every other surfaced text field's content (worker
strings get a `not worker.strip()` check at `engine.py:1262`), but
`summary` has zero validation. A card may carry:

```yaml
summary: ""
summary: "   "
```

…and `goc validate` returns OK.

Meanwhile, `_cmd_quality_pass` at `engine.py:3180` already treats both
shapes as a quality defect:

```python
summary = (c.summary or "").strip() if hasattr(c, "summary") else ""
if not summary:
    missing_summary.append(c.title)
```

So one surface (`goc quality-pass`) flags the card; the other (`goc
validate`) silently passes it. The contract is inconsistent.

This mirrors the gap the recently-closed cards
[validate-accepts-whitespace-only-worker-as-non-empty](../validate-accepts-whitespace-only-worker-as-non-empty/)
and
[validate-accepts-whitespace-only-worker-where-as-non-empty](../validate-accepts-whitespace-only-worker-where-as-non-empty/)
fixed for the `worker` field — same shape, different field.

## Empirical evidence

Running `reproduce.py` (a tempdir-scoped deck with one card carrying
`summary: "   "`) against `goc validate`:

```
# `goc validate` with summary: "   "
exit_code: 0
stdout:

stderr:

DEFECT CONFIRMED: validate accepted whitespace-only summary (should reject with same message shape as the worker fix).
```

## Why it matters

**Reachability path.** A whitespace-only summary reaches the deck via
two well-trodden routes: (1) `goc new <title>` scaffolds frontmatter
with `summary: ""` (see the bare-string emit at
`engine.py:_yaml_inline`), and the author may forget to populate it,
or write a single space and tab away; (2) the inline emitter's quoting
rules preserve a hand-typed `summary: "   "` round-trip. Both shapes
land in the committed README. Today the deck has zero such cards (the
release tripwire would not have caught them either) but the gap will
silently accept the next instance.

The contract drift between `validate` (silent) and `quality-pass`
(flagged) means a card author who only runs the validator never learns
their summary is empty until a separate hygiene pass surfaces it.

## Fix

Add a `summary` content check to `validate_card` adjacent to the
existing `worker` block (around `engine.py:1259`):

```python
summary_value = fm.get("summary")
if summary_value is not None:
    if not isinstance(summary_value, str):
        errors.append(f"{t.title}: summary: must be a string")
    elif not summary_value.strip():
        errors.append(f"{t.title}: summary: must not be empty or whitespace-only")
```

Add a regression test mirroring `tests/test_validate_worker_whitespace.py`
(`tests/test_validate_summary_whitespace.py`) covering: bare empty,
whitespace-only, and a positive control.

## Sibling-sweep note

`definition_of_done` exhibits the *same* gap (the validator only checks
`isinstance(fm["definition_of_done"], str)` at `engine.py:1234`, so
`definition_of_done: ""` and `definition_of_done: "   "` also pass).
That is a separate card, not part of this fix. If a fourth instance of
this pattern surfaces, file the architectural meta-fix (a centralized
non-empty-string-field helper) instead of a fourth single-field card.

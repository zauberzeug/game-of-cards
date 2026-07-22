---
title: waiting-until-with-trailing-newline-passes-wait-then-crashes-reads
status: done
stage: null
contribution: high
created: "2026-07-22T01:47:18Z"
closed_at: "2026-07-22T01:56:58Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: goc wait --until accepts a date with a trailing newline ("2026-08-01\n") because _ISO_DATE_RE's $ anchor matches before a final newline and _is_iso_date calendar-parses only the truncated 10-char prefix. The value round-trips to disk as a block scalar, and every full-value reader (_waiting_until_instant, reached from goc validate and goc --waiting) then crashes with an uncaught ValueError traceback.
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (wait rejects the trailing-newline date with exit 2, and validate/--waiting no longer traceback on a hand-written trailing-newline waiting_until)
  - [x] TDD: regression test covers _is_iso_date rejecting "2026-08-01\n" and "2026-05-20T12:00:00Z\n", and goc validate FAILing (not crashing) on a stored trailing-newline waiting_until
  - [x] MECHANICAL: _ISO_DATE_RE and _ISO_DATETIME_UTC_RE anchor with \Z (or equivalent) so the shape check cannot pass values the consumers cannot parse
  - [x] MECHANICAL: _is_iso_date parses the full string value, not the _date_part truncation, so predicate == parser as its own docstring claims
worker: {who: "claude[bot]", where: main}
---

# waiting-until-with-trailing-newline-passes-wait-then-crashes-reads

`goc wait <card> --until $'2026-08-01\n'` exits 0 and persists the
newline; afterwards `goc validate` and `goc --waiting` crash with an
uncaught `ValueError: Invalid isoformat string: '2026-08-01\n'`.

## Location

- `goc/engine.py:1051` — `_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")`
- `goc/engine.py:1076` — `date.fromisoformat(_date_part(value))` inside `_is_iso_date`
- `goc/engine.py:1137` — `d = date.fromisoformat(value)` inside `_waiting_until_instant` (the crash site)
- `goc/engine.py:5752` — `_cmd_wait` input validation that lets the value in

## What's broken

Python's `$` anchor matches *before a trailing newline*, so
`"2026-08-01\n"` passes the `_ISO_DATE_RE` shape check. The calendar
confirmation then parses only the truncated prefix:

```python
date.fromisoformat(_date_part(value))   # engine.py:1076 — value[:10], drops the "\n"
```

so `_is_iso_date("2026-08-01\n")` returns True and `goc wait --until`
accepts the value (engine.py:5752). Because the string ends with a
newline, `emit_frontmatter` writes it as a block scalar
(`waiting_until: |`), and the frontmatter parser faithfully restores
the trailing newline on the next read.

The reader then parses the FULL value:

```python
d = date.fromisoformat(value)           # engine.py:1137 — raises ValueError
```

This contradicts `_is_iso_date`'s own docstring (engine.py:1063-1069):

> Match the predicate to the parser by parsing with the SAME calendar
> the consumer uses — the full timestamp for the datetime shape, not
> just the date prefix.

The date-only shape does exactly what the docstring forswears: it
parses just the date prefix. `_waiting_until_instant`'s docstring
(engine.py:1122) also claims "Returns None for anything `_is_iso_date`
rejects (the malformed-value backstop)" — but the backstop never fires
because `_is_iso_date` *accepts* the value it cannot parse.

The datetime shape is not crash-reachable through `wait` — for
`"2026-05-20T12:00:00Z\n"` the predicate strptime-parses the full
value and rejects it — but its regex has the same `$` anchor and
deserves the same fix.

## Empirical evidence

```
$ goc wait probe-card --until $'2026-08-01\n'
probe-card: waiting_on=None waiting_until='2026-08-01\n' (no reason set; implied 'deferred')
$ echo $?
0
$ goc validate
Traceback (most recent call last):
  ...
  File ".../goc/engine.py", line 1137, in _waiting_until_instant
    d = date.fromisoformat(value)
ValueError: Invalid isoformat string: '2026-08-01\n'
```

Once the card is non-draft, `goc --waiting` crashes identically
through `waiting_impedes` (engine.py:2497).

## Why it matters

An accepted CLI input persists a value the engine's own readers
cannot parse, and the tool that should diagnose the bad state —
`goc validate` — is itself the crasher, so the deck is bricked for
every read surface that touches the waiting overlay until the
frontmatter is hand-edited. Reachability: `goc wait --until` with a
trailing newline in the argument (trivially produced by shell command
substitution, e.g. `--until "$(date -d tomorrow +%F)"` variants that
capture a newline, or copy-paste). This is the third instance of the
predicate/parser mismatch family after
[waiting-until-with-impossible-time-passes-validate-then-crashes-reads](../waiting-until-with-impossible-time-passes-validate-then-crashes-reads/)
(impossible time component) and
[waiting-impedes-truncates-malformed-waiting-until-to-a-valid-prefix-date](../waiting-impedes-truncates-malformed-waiting-until-to-a-valid-prefix-date/)
(prefix garbage) — both closed with a "predicate == parser" fix that
the trailing-newline shape defeats via the `$` anchor plus
`_date_part` truncation.

The same `$`-anchor shape also lets trailing-newline card *titles*
through `goc new` / `goc move` / `validate` — filed separately as
[trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir](../trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir/)
(different validator, different blast radius).

## Fix (landed)

1. Both regexes anchor with `\Z`:
   `_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\Z")` and
   `_ISO_DATETIME_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")`
   (goc/engine.py).
2. `_is_iso_date` parses the full value —
   `date.fromisoformat(value)` instead of
   `date.fromisoformat(_date_part(value))` — so the predicate matches
   the parser even if the shape check regresses.

Verified post-fix: `goc wait --until $'2026-08-01\n'` rejects the
value at input time (exit 2, `reproduce.py` prints `[OK] defect no
longer fires`), a legacy stored value now FAILs `validate_card`'s
existing `_is_iso_date(fm["waiting_until"])` check instead of
certifying OK, and `_waiting_until_instant`'s None backstop keeps
`goc --waiting` / `validate_waiting_overlay` alive instead of
crashing. Regression coverage:
`tests/test_iso_date_trailing_newline.py` (6 tests).

---
title: waiting-impedes-truncates-malformed-waiting-until-to-a-valid-prefix-date
summary: "The read-time guard `waiting_impedes` parses `waiting_until` via `_date_part`, which prefix-truncates any >=10-char string to its first 10 chars. A malformed value like `2026-05-20xx` (which `goc validate` rejects) parses cleanly to a past date and silently un-defers the card, re-entering the pull queue. This defeats the impede-on-malformed backstop installed by the closed sibling card, whose fix relies on `date.fromisoformat` raising — which truncation prevents."
status: open
stage: null
contribution: medium
created: "2026-05-27T03:18:36Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (prefix-valid garbage like `2026-05-20xx` reports `impeded=True`, same as total garbage and bare-reason).
  - [ ] TDD: fix in `goc/engine.py` `waiting_impedes` — treat a `waiting_until` the validator would reject (fails `_is_iso_date` / the anchored ISO shape) as unparseable, falling through to `until_unparseable=True` instead of accepting a truncated prefix.
  - [ ] TDD: `validate_waiting_overlay` mirrors the same strictness — a value rejected by `_is_iso_date` does not silently `continue` as if absent (decide: skip vs. surface, but do not parse-by-truncation).
  - [ ] TDD: no behavior change for valid date-only, valid datetime-UTC, future, and elapsed `waiting_until`, nor for the bare-reason / no-overlay paths.
---

# `waiting_impedes` truncates a malformed `waiting_until` to a valid prefix date

## Location

`goc/engine.py:1660-1662` (`waiting_impedes`) and the shared helper
`goc/engine.py:692-697` (`_date_part`). The same truncation underlies
`validate_waiting_overlay` at `goc/engine.py:1378-1379`.

## What's broken

`waiting_impedes` decides whether a card carries an active impediment by
parsing `waiting_until`:

```python
if until is not None:
    try:
        until_date = date.fromisoformat(_date_part(until))
    except (TypeError, ValueError):
        # Malformed date: ... Err on the side of impeding
        # so the card is not silently un-deferred ...
        until_date = None
        until_unparseable = True
```

The `except` branch — the protection installed by the closed card
[waiting-impedes-treats-malformed-waiting-until-as-no-impediment](../waiting-impedes-treats-malformed-waiting-until-as-no-impediment/)
— only fires when `date.fromisoformat(...)` raises. But it is fed through
`_date_part`, which **prefix-truncates**:

```python
def _date_part(value) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return str(value)
```

So a malformed value like `"2026-05-20xx"` is truncated to `"2026-05-20"`,
which `date.fromisoformat` parses **without raising**. The malformed-impede
branch is unreachable for any garbage whose first 10 chars happen to be a
valid calendar date. The card is treated as having a real (past) date and is
silently un-deferred — exactly the failure the sibling card was filed to
prevent, just via a different input class.

This contradicts the validator. `_is_iso_date` (`goc/engine.py:662-681`) is
anchored full-string (`^\d{4}-\d{2}-\d{2}$` / the datetime variant) and parses
the calendar, so `goc validate` **rejects** `"2026-05-20xx"`:

```python
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")   # engine.py:658
```

```
waiting_until: '2026-05-20xx' not a valid ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ date
```

`_is_iso_date` is safe because `_date_part` there runs only *after* the
anchored regex already confirmed the whole string is well-formed. The read-time
guards (`waiting_impedes`, `validate_waiting_overlay`) call `_date_part`
directly on raw frontmatter with no prior shape check, so the lenient
truncation leaks through.

## Empirical evidence

```
== input the validator rejects ==
  _is_iso_date('2026-05-20xx') = False
  _date_part('2026-05-20xx')   = '2026-05-20'

== waiting_impedes (today = 2026-05-27) ==
  prefix-garbage '2026-05-20xx' -> impeded=False  (EXPECTED True)
  total-garbage  'not-a-date'   -> impeded=True  (control: True)
  no date, reason set           -> impeded=True  (control: True)

DEFECT CONFIRMED: prefix-valid garbage un-defers the card (impeded=False) while total garbage and bare-reason both impede.
```

## Why it matters

The closed sibling card establishes the read-time guard as the backstop for
"live, pre-validate decks (queue renders run without a prior `goc validate`),
so a hand-edited or mid-write card can hit this." That backstop is now only
partial: it protects against *un*-shaped garbage (`not-a-date`) but not against
*prefix-valid* garbage (`2026-05-20xx`, `2026-05-20 (note)`, a trailing
timezone-ish suffix, a date with an appended comment). A hand-edited card with
`waiting_on: external` and such a value silently rejoins the `pull-card` /
`next-card` queue — a card the human meant to defer gets autonomously pulled.

## Fix

Make the read-time guard mirror the validator's strictness rather than parsing
by truncation. In `waiting_impedes`, gate the parse on the same full-string
shape the validator uses — e.g. treat the value as unparseable when
`_is_iso_date(until)` is false (set `until_unparseable = True`), only calling
`_date_part`/`fromisoformat` once the shape is confirmed. Apply the same gate
in `validate_waiting_overlay` so a rejected value is not parsed via its prefix.
A narrower alternative is to tighten `_date_part` itself to refuse truncation
of non-ISO-shaped strings, but that helper is also used in safe post-regex
contexts, so gating at the two read-time call sites is lower-risk. **Do not
apply the fix** — this card flags it; `pull-card` implements.

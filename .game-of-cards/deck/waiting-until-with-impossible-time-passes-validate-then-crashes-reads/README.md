---
title: waiting-until-with-impossible-time-passes-validate-then-crashes-reads
summary: "`_is_iso_date` only calendar-validates the date prefix (`value[:10]`), so a `waiting_until` with an ISO-shaped but impossible TIME like `2026-05-20T25:61:99Z` passes `goc validate`. The consumer `_waiting_until_instant` then parses the full timestamp with `strptime` and raises an uncaught `ValueError` — crashing `goc validate`, `waiting_impedes`, and every queue read of a deck that contains such a card. Same validator-weaker-than-parser shape as the closed date-prefix card, but for the time component, and the failure is a hard crash rather than a silent un-defer."
status: done
stage: null
contribution: high
created: "2026-05-27T04:03:30Z"
closed_at: 2026-05-27T05:35:32Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — `_is_iso_date('2026-05-20T25:61:99Z')` returns False and `goc validate` rejects (clean FAIL, no traceback) a card whose `waiting_until` carries an impossible time component.
  - [x] TDD: `waiting_impedes` on a card with an impossible-time `waiting_until` returns a bool (treats it as still-impeding, same backstop contract as the date-prefix sibling) instead of raising `ValueError`.
  - [x] TDD: no behavior change for genuinely valid date/datetime shapes — valid `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SSZ` values still parse and impede/clear exactly as before (existing waiting-overlay tests stay green).
  - [x] MECHANICAL: the `_is_iso_date` docstring (engine.py:667-670) stays accurate — it currently claims it "matches the predicate to the parser", which is false for the time component until this lands.
worker: {who: "claude[bot]", where: main}
---

# `waiting_until` with an impossible time passes `goc validate`, then crashes every read

## Location

- `goc/engine.py:658-681` — `_ISO_DATETIME_UTC_RE` + `_is_iso_date` (the validator's date/datetime predicate).
- `goc/engine.py:692-697` — `_date_part`, which truncates to `value[:10]` (date prefix only).
- `goc/engine.py:700-727` — `_waiting_until_instant`, which parses the full timestamp with `strptime("%Y-%m-%dT%H:%M:%SZ")`.
- `goc/engine.py:1716-1740` — `waiting_impedes`, the read-time guard that calls `_waiting_until_instant` with no `try/except`.

## What's broken

`_is_iso_date` was tightened (by the closed
[validate-accepts-calendar-impossible-dates-that-un-defer-cards](../validate-accepts-calendar-impossible-dates-that-un-defer-cards/))
to parse the calendar, but only the **date prefix**:

```python
def _is_iso_date(value) -> bool:
    ...
    if not (_ISO_DATE_RE.match(value) or _ISO_DATETIME_UTC_RE.match(value)):
        return False
    try:
        date.fromisoformat(_date_part(value))   # _date_part == value[:10]
    except ValueError:
        return False
    return True
```

`_ISO_DATETIME_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")`
matches the **shape** of the time component but never range-checks it, and
`_date_part` throws the time away (`value[:10]`). So `2026-05-20T25:61:99Z`
(hour 25, minute 61, second 99) matches the regex, has a valid date prefix
`2026-05-20`, and `_is_iso_date` returns `True`. `validate_card` trusts that
predicate and emits **no error**.

But the consumer parses the full timestamp:

```python
def _waiting_until_instant(value) -> datetime | None:
    ...
    elif _ISO_DATETIME_UTC_RE.match(value):
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")   # raises on 25:61:99
```

`strptime` range-checks, raises `ValueError`, and **nothing catches it**.
`waiting_impedes` (engine.py:1721-1722) calls `_waiting_until_instant(until)`
expecting `None` for malformed input, but here it raises:

```python
if until is not None:
    until_dt = _waiting_until_instant(until)   # <-- raises, not None
    if until_dt is None:
        ...
```

The docstring on `_waiting_until_instant` even claims it "Returns None for
anything `_is_iso_date` rejects" — but `_is_iso_date` *accepts* this value, so
the None-backstop never engages. The `_is_iso_date` docstring's promise (lines
667-670) — "Match the predicate to the parser by also parsing the date
portion" — is literally true (it parses the *date* portion) and substantively
false (it never parses the *time* portion the parser actually uses).

This is the same validator-strictly-weaker-than-consumer-parser bug the
date-prefix sibling fixed, one level down: the prior fix closed the
`YYYY-MM-DD` calendar gap; the `HH:MM:SS` calendar gap remains. And the
failure mode is worse — the date-prefix bug *silently un-deferred* a card; this
one raises an **uncaught exception** that aborts `goc validate`,
`waiting_impedes`, `card_is_ready`, `compute_values` (which calls
`waiting_impedes` at engine.py:1833), and therefore every table/board/queue
render of a deck containing the card.

## Empirical evidence

Before the fix:

```
_is_iso_date('2026-05-20T25:61:99Z')      = True    (EXPECTED False)
_waiting_until_instant(...)                 -> RAISED ValueError: time data '2026-05-20T25:61:99Z' does not match format '%Y-%m-%dT%H:%M:%SZ'
waiting_impedes(card with that until)       -> RAISED ValueError (EXPECTED a bool)
DEFECT CONFIRMED: validator accepts an impossible time the read-time guard then crashes on.
```

After the fix (reproduce.py exits 0):

```
_is_iso_date('2026-05-20T25:61:99Z')      = False    (EXPECTED False)
_waiting_until_instant(...)                 -> returned without raising
waiting_impedes(card with that until)       -> returned True
FIXED: impossible time rejected by the predicate and waiting_impedes is total.
```

## Why it matters

`goc validate` is documented as the upstream safety net for hand-edited and
pre-validate decks (the read-time guards explicitly defer to it — see the
comment at engine.py:1727-1729). A frontmatter value that the validator
green-lights must never crash a downstream read. Here a single hand-typed or
copy-pasted `waiting_until` (a plausible typo: `T25:` for `T05:`, or a
seconds-rollover `:99`) makes the *entire deck* unreadable — every `goc`,
`goc --board`, `goc validate`, and the autonomous pull/next queue
aborts with a traceback until the offending card is found and hand-fixed,
which is hard precisely because the listing commands that would surface it
also crash.

## Fix (applied)

Matched the predicate to the parser fully. In `_is_iso_date` (engine.py:662-684),
when the value is the datetime shape, it is now parsed with the **same**
`strptime` the consumer uses (not just the date prefix):

```python
try:
    if _ISO_DATETIME_UTC_RE.match(value):
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    else:
        date.fromisoformat(_date_part(value))
except ValueError:
    return False
return True
```

That single change makes `_is_iso_date` reject the impossible time, so
`validate_card` emits its clean FAIL and `_waiting_until_instant`'s
`_is_iso_date` gate returns `None` for it — restoring the
treat-malformed-as-impeding backstop in `waiting_impedes` exactly as the
date-prefix sibling intended. The root-cause predicate fix keeps the two
functions consistent; no `try/except` patch was needed in
`_waiting_until_instant`.

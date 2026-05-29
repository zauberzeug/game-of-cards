---
title: validate-accepts-calendar-impossible-dates-that-un-defer-cards
summary: "`goc validate`'s date check (`_is_iso_date`) is regex-shape only, so a calendar-impossible-but-ISO-shaped `waiting_until` like `2026-13-45` passes validation. The read-time guard `waiting_impedes` then parses it with `date.fromisoformat`, fails, and — for a bare deferral with no `waiting_on` — silently un-impedes the card, re-admitting it to the pull queue. The validator predicate is strictly weaker than the consumer's parser."
status: done
stage: null
contribution: medium
created: "2026-05-27T02:13:54Z"
closed_at: "2026-05-27T02:20:14Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — `_is_iso_date('2026-13-45')` returns False and `goc validate` rejects a card whose `waiting_until` is a calendar-impossible date.
  - [x] TDD: a bare-deferral card (`waiting_until` only, no `waiting_on`) carrying a calendar-impossible date no longer escapes `waiting_impedes` — chosen contract (both): it cannot pass validate AND `waiting_impedes` treats an unparseable bare date as still-impeding. reproduce.py asserts both.
  - [x] TDD: no behavior change for genuinely valid date/datetime shapes (`created`, `closed_at`, `waiting_until` for valid past/future dates) — the existing control paths stay green.
  - [x] MECHANICAL: the `_is_iso_date` docstring / the validate error message stay accurate to the tightened predicate.
worker: {who: "claude[bot]", where: main}
---

# `goc validate` accepts calendar-impossible dates, which silently un-defer cards

## Location

- `goc/engine.py:658-670` — `_ISO_DATE_RE` + `_is_iso_date` (the validator's date predicate).
- `goc/engine.py:1102-1107`, `1151-1155` — `validate_card` uses `_is_iso_date` for `created`, `closed_at`, `waiting_until`.
- `goc/engine.py:1640-1658` — `waiting_impedes` parses `waiting_until` with `date.fromisoformat`.

## What's broken

The validator's date predicate checks shape, not calendar validity:

```python
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _is_iso_date(value) -> bool:
    ...
    return bool(_ISO_DATE_RE.match(value) or _ISO_DATETIME_UTC_RE.match(value))
```

`2026-13-45` (month 13, day 45) matches `\d{4}-\d{2}-\d{2}` and so passes
`_is_iso_date`. `validate_card` therefore emits **no error**, even though the
message it would emit promises a real date:

```python
if "waiting_until" in fm and fm["waiting_until"] is not None:
    if not _is_iso_date(fm["waiting_until"]):
        errors.append(
            f"{t.title}: waiting_until: {fm['waiting_until']!r} not ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ"
        )
```

But the read-time guard parses with the real calendar and silently drops the value:

```python
until = card.waiting_until
until_date: date | None = None
if until is not None:
    try:
        until_date = date.fromisoformat(_date_part(until))   # raises on 2026-13-45
    except (TypeError, ValueError):
        until_date = None
if reason is None and until_date is None:
    return False        # <-- bare deferral with bad date: NOT impeded
```

For a **bare deferral** (`waiting_until` set, `waiting_on` unset), a
calendar-impossible date makes `until_date = None` and `reason = None`, so
`waiting_impedes` returns `False` — the card is no longer hidden and
re-enters the `pull-card` / `next-card` queue. The validator that is supposed
to be the safety net does not catch it, because `_is_iso_date` (regex shape)
is strictly weaker than `date.fromisoformat` (calendar-valid). The two
predicates disagree on exactly the inputs that matter.

## Relationship to the prior fix

The done card
[waiting-impedes-treats-malformed-waiting-until-as-no-impediment](../waiting-impedes-treats-malformed-waiting-until-as-no-impediment/)
fixed the `waiting_on` + garbage-date path (fall through to the reason check)
and justified leaving the bare-date path alone with:

> Severity is bounded: `validate_card` rejects a non-ISO `waiting_until`, so a
> *validated* deck cannot hold one.

That assumption is false for calendar-impossible-but-ISO-shaped dates: `validate`
does **not** reject `2026-13-45`. So a validated deck *can* hold a bare
`waiting_until` that `waiting_impedes` silently ignores. This card closes that
gap at the predicate level rather than per-call-site.

## Empirical evidence

```
_is_iso_date('2026-13-45'): True
waiting_impedes(bare deferral, waiting_until=2026-13-45): False   # defect: should be hidden/rejected
waiting_impedes(bare deferral, waiting_until=2099-01-01): True    # control: valid future date hides
```

(See `reproduce.py`.)

## Why it matters

`waiting_until` is the deferral mechanism: a card parked until a future date is
supposed to stay out of the autonomous pull queue until then. A typo'd month or
day (`2026-13-01`, `2026-02-30`) passes validation but defeats the guard, so the
deferred card is silently pulled — the opposite of the author's intent — and no
`goc validate` run flags the bad date. The same regex-only gap affects `created`
and `closed_at`, which are parsed with `date.fromisoformat` by triage/age and
elapsed-wait surfacing (`engine.py:1364`, `engine.py:4161`).

## Fix (applied)

Two changes, belt and suspenders:

1. **`_is_iso_date` now parses the calendar.** After the regex shape check it
   calls `date.fromisoformat(_date_part(value))` and returns `False` on
   `ValueError`. The predicate now matches the consumer's parser, so `goc
   validate` rejects calendar-impossible dates in `created`, `closed_at`, and
   `waiting_until` (and the `goc wait --until` CLI guard) in one place —
   restoring the "validated deck cannot hold an unparseable date" invariant the
   prior fix relied on.
2. **`waiting_impedes` backstops un-validated decks.** A present-but-unparseable
   `waiting_until` now keeps the card impeded (returns `True`) instead of
   silently un-deferring it — for a bare deferral as well as alongside a
   `waiting_on`. The validator is the upstream net; this is the read-time
   backstop for pre-validate / hand-edited decks.

The three validator/CLI date-error messages now read "not a valid ISO … date"
to signal that calendar validity (not just shape) is enforced. `reproduce.py`
asserts both contracts plus the valid date/datetime controls.

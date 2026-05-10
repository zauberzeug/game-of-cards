---
title: record-card-timestamps-as-utc-datetime
summary: |
  Card frontmatter currently stores `created` and `closed_at` as date-only
  strings (`YYYY-MM-DD`). Fast-moving projects close several cards per day,
  so date-only timestamps tie on sort order and prevent meaningful velocity
  computation. Upgrade both fields to ISO 8601 UTC datetime
  (`YYYY-MM-DDTHH:MM:SSZ`) while keeping backwards compatibility with
  existing date-only entries.
status: open
stage: null
contribution: medium
created: 2026-05-10
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [meta-fix, documentation]
definition_of_done: |
  - [ ] decision recorded below for which migration strategy lands
  - [ ] `_is_iso_date` (or successor) accepts both date-only and full
        ISO 8601 UTC datetime in `goc/engine.py`
  - [ ] `goc new` writes datetime for `created`
  - [ ] `goc done` writes datetime for `closed_at`
  - [ ] sort key in `goc/engine.py` (lines around 1054 and 2839) still
        orders correctly across mixed date-only and datetime entries
  - [ ] `--since` filter (engine.py:982) still works with mixed shapes
  - [ ] `goc validate` passes on this repo's deck (legacy date-only
        cards must remain valid)
  - [ ] schema doc in `Skill(card-schema)` describes the new shape and
        the legacy fallback
---

# record-card-timestamps-as-utc-datetime

## What's missing

`goc/engine.py` writes `created` and `closed_at` as `date.today().isoformat()`
— a `YYYY-MM-DD` string with no time component. The validator (`_is_iso_date`)
requires that exact shape and rejects anything else. On a deck closing
multiple cards per day, this loses ordering information and makes velocity
analysis (cards closed per hour, time-to-close distributions) impossible.

Concrete sites:

- `goc/engine.py:1932` — `goc done` writes date-only `closed_at`.
- `goc/engine.py:2554` — `goc new` writes date-only `created`.
- `goc/engine.py:748,752` — validator demands `_is_iso_date`.
- `goc/engine.py:1054,2839` — sort key uses `t.created` as a string.
- `goc/engine.py:982` — `--since` filter uses `closed_at` string compare.

## Why it matters

This repo (the goc source tree) closed a documented incident on 2026-05-05
where parallel-day card activity could not be reconstructed from
frontmatter alone — git timestamps had to be cross-referenced. As GoC adoption
grows (OpenClaw plugin landed; multiple agents may close cards in one day),
the gap widens. Velocity views (`goc --done`, retrospective skill output)
flatten to per-day buckets, so trends within a day are invisible.

The lexicographic sort property of ISO 8601 means a mixed deck stays
sortable: `"2026-05-10"` < `"2026-05-10T14:00:00Z"` < `"2026-05-11"` orders
correctly under string compare. So the validator can be widened without a
backfill rewrite.

## Decision required

Three credible migration paths; only one should land.

### Option A — accept both shapes, write datetime going forward

- Validator accepts `YYYY-MM-DD` OR `YYYY-MM-DDTHH:MM:SSZ`.
- `goc new` and `goc done` write datetime.
- Old cards keep their date-only fields; sorts and filters keep working
  via lexicographic order.
- **Cost**: minimal — one validator change, two emit sites change.
- **Trade-off**: deck has mixed shapes forever. Anyone reading a card
  notices the inconsistency. Velocity computation is undefined for
  pre-migration cards.

### Option B — accept both shapes, backfill old cards once

- Same as A, plus a one-shot `scripts/backfill_card_times.py` that
  rewrites every existing `created` and `closed_at` to a synthetic
  midnight-UTC datetime (`T00:00:00Z`).
- **Cost**: writes every card directory in one commit; merge conflict
  risk for any in-flight branches.
- **Trade-off**: synthetic times are misleading — they look precise but
  are not. Confuses anyone analyzing pre-migration velocity.

### Option C — add separate `created_at` / `closed_at_utc` fields

- Leave `created` and `closed_at` as date-only (compatibility forever).
- Add `created_at` and `closed_at_utc` as new optional fields holding the
  full datetime.
- New cards write both; old cards have only the legacy fields.
- **Cost**: schema gets two new fields; downstream readers need to know
  which to prefer.
- **Trade-off**: dual-source-of-truth problem; field bloat. Every code
  path that reads `created` now has to decide whether to prefer
  `created_at` if present.

**Recommendation**: Option A. Lexicographic sort is the lever that makes
mixed shapes work without backfill. Velocity computation becomes accurate
for new cards immediately and degrades gracefully for old ones (date-only
sorts to start of day). Option B's synthetic times are misleading;
Option C's dual fields are schema bloat for marginal gain.

## Fix sketch (if Option A)

```python
# goc/engine.py
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

def _is_iso_date_or_datetime(value: str) -> bool:
    return bool(_ISO_DATE.match(value) or _ISO_DATETIME_UTC.match(value))
```

`goc new` writes `datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`;
`goc done` does the same. Sort key remains a string compare — no change
needed because `"2026-05-10"` < `"2026-05-10T00:00:00Z"` < `"2026-05-10T15:00:00Z"`.

## Notes

- Do not embed local timezone offsets — that breaks lexicographic sort
  and makes cross-machine analysis ambiguous. UTC only.
- `goc validate` should print a warning (not error) when it sees a
  date-only entry, to nudge eventual cleanup without breaking decks.
- After the engine change, update `Skill(card-schema)` body to describe
  the new shape and the legacy fallback rule.

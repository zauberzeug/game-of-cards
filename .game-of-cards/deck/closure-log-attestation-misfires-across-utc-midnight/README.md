---
title: closure-log-attestation-misfires-across-utc-midnight
summary: "UNVERIFIED. The `log-md-closure-entry` derived check matches the log.md closure header against `today` (`_utc_now_iso` at attest time). A closure entry written on one UTC day and attested on the next won't match — the `## <yesterday> — Closure` header is searched for `## <today>`. Distinct from the closed read-time-date-guards card (that fixed local-vs-UTC, not write-day-vs-attest-day). Needs a reproduce.py proving the misfire via a real attest path."
status: open
stage: null
contribution: low
created: "2026-05-27T08:02:35Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: reproduce.py shows the closure check returning False for a log.md whose `## YYYY-MM-DDTHH:MM:SSZ — Closure` header is dated the day before the injected `today`.
  - [ ] PROCESS: decide the fix — match any well-formed closure header regardless of date, or compare against the card's own `closed_at` rather than wall-clock `today`. Record in log.md.
  - [ ] MECHANICAL: `goc validate` clean; plugin mirrors synced.
---

# Closure-log attestation misfires across a UTC midnight boundary

UNVERIFIED — cited code read and confirmed present, but no `reproduce.py`
exercised this round. Park with a falsification recipe.

## Hypothesis (file:line)

`goc/engine.py:3417-3430` (`_run_derived_check`, `log-md-closure-entry`):

```python
date_prefix = _date_part(today)
pattern = re.compile(
    rf"^## {re.escape(date_prefix)}(?:T\d{{2}}:\d{{2}}:\d{{2}}Z)? — Closure",
    re.MULTILINE,
)
if pattern.search(log_path.read_text()):
    return True, f"'## {date_prefix} — Closure' present"
return False, f"no '## {date_prefix} — Closure' section"
```

`today` is `_utc_now_iso()` captured at attest time (engine.py:3481). The
pattern only matches a closure header bearing **today's** date. A closure
entry written just before UTC midnight and attested after it carries a
`## <yesterday> — Closure` header, which the `## <today>` pattern misses —
the check fails despite a valid closure entry.

## Why deferred

Reachability depends on whether closure-entry write and attest can land on
different UTC days. In the common `goc done` flow both happen in one
invocation, so the dates match. The misfire requires a separate `goc attest`
run on a later day (or a write that crosses midnight mid-invocation). This is
distinct from the closed
[read-time-date-guards-compare-utc-stamps-to-local-date](../read-time-date-guards-compare-utc-stamps-to-local-date/),
which fixed local-vs-UTC drift in `waiting_impedes` / `validate_waiting_overlay`
/ triage aging — it did not touch this closure-entry check. One filed card
consumed this audit round's verification budget.

## Falsification recipe

1. Write a card's `log.md` with `## 2026-05-26T23:59:00Z — Closure`.
2. Call `_run_derived_check` (or run `goc attest`) with `today="2026-05-27..."`.
3. If it returns `(False, "no '## 2026-05-27 — Closure' section")`, the defect
   is real → promote (drop `unverified`, add a working `reproduce.py`).
4. If closure-write and attest are provably always the same invocation/day,
   disprove.

---
title: closure-log-attestation-misfires-across-utc-midnight
summary: "`goc attest`'s `log-md-closure-entry` check only accepted a closure heading dated attest's own UTC day, so an entry written before midnight and attested after it — or re-attested on a later day — read as missing, and append-only log.md left a duplicate entry as the only way back to a pass. Reproduced on the real attest path. Fixed by accepting any well-formed closure heading whatever day it names; the hand-typed stamp says nothing about freshness, as 91 of this deck's 370 attested closure headings run ahead of the attest that verified them."
status: done
stage: null
contribution: low
created: "2026-05-27T08:02:35Z"
closed_at: "2026-10-31T05:45:34Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py shows the closure check returning False for a log.md whose `## YYYY-MM-DDTHH:MM:SSZ — Closure` header is dated the day before the injected `today`.
  - [x] TDD: `tests/test_closure_entry_check_ignores_heading_date.py` pins the fixed contract on the predicate and on the real `goc attest` path, and pins that a log without a closure heading — attest's own verification block included — still fails.
  - [x] PROCESS: decide the fix — match any well-formed closure header regardless of date, or compare against the card's own `closed_at` rather than wall-clock `today`. Record in log.md.
  - [x] MECHANICAL: `goc validate` clean; plugin mirrors synced.
worker: {who: "claude[bot]", where: main}
---

# Closure-log attestation misfires across a UTC midnight boundary

## Location

`goc/engine.py` — `_CLOSURE_HEADING_RE` (line 6392) and the
`log-md-closure-entry` branch of `_run_derived_check` (line 6426), which
`_cmd_attest` runs at Step 5 of `Skill(finish-card)`.

## What was broken

The check built its pattern from attest's wall clock:

```python
date_prefix = _date_part(today)          # today = _utc_now_iso() at attest time
pattern = re.compile(
    rf"^## {re.escape(date_prefix)}(?:T\d{{2}}:\d{{2}}:\d{{2}}Z)? — Closure",
    re.MULTILINE,
)
```

Only a closure heading dated attest's own UTC day matched. The heading is
typed by hand at Step 4 and attest runs at Step 5, so three ordinary flows
failed the check on an entry that was there:

- the entry is written before UTC midnight and attest runs after it;
- attest fails for another reason (an open `advanced_by` prerequisite) and
  is re-run on a later day, after the prerequisite closes;
- the closer's clock is ahead and the typed stamp names tomorrow.

The failure message, `no '## <today> — Closure' section`, said the section
was missing. log.md is append-only, so the only way back to a pass was a
second closure entry.

## Empirical evidence

`reproduce.py` (exit 0 = defect gone, 1 = defect fires, 2 = harness broken)
runs two probes. In the predicate probe, `_run_derived_check` gets an injected
`today` of `2026-05-27T00:01:00Z`. In the shipped-path probe, the real
`goc attest --non-interactive` runs on the real clock against a heading
stamped 23:59:00Z yesterday. That is the log a pre-midnight entry leaves for
a post-midnight run, so no clock has to be faked. Before the fix it exits 1:

```
  heading written 23:59:00Z the day before      -> False: no '## 2026-05-27 — Closure' section   [MISFIRE]
  legacy date-only heading from the day before  -> False: no '## 2026-05-27 — Closure' section   [MISFIRE]
  heading written three days before             -> False: no '## 2026-05-27 — Closure' section   [MISFIRE]
...
closure heading stamp: 2026-10-30T23:59:00Z  (written one minute before last midnight)
exit code: 2
  [ ] log-md-closure-entry — no '## 2026-10-31 — Closure' section
DEFECT REPRODUCED: ...
```

After it, every case passes, the no-heading control still fails, and attest
exits 0 with `[x] log-md-closure-entry — '## 2026-10-30T23:59:00Z — Closure' present`.

The stamp is a guess, not a timestamp. Of the 370 datetime closure
headings in this deck that sit above a passing attest block, 91 are stamped
*later* than that engine-clocked run, six of them by over an hour and one by
8 hours (`set-cadence-retunes-earlier-workflows-before-validating-later-specs`:
heading 09:30:00Z, attest 01:24:50Z). 46 cards carry a `T00:00:00Z`
placeholder time. No deck card recorded a cross-day misfire, but each of
those near-misses would have been one if the guess had crossed a UTC
midnight.

## Decision

*Resolved 2026-10-22T05:56:37Z:* Lower the gate: verify, then make the closure-entry match tolerate the UTC day boundary

*Reasoning:* Bulk rule approved by the maintainer in a human session on 2026-10-22: a gated card with no written question and a mechanical fix drops to gate none

## Fix

- **Any well-formed closure heading counts, whatever day it names.**
  `_CLOSURE_HEADING_RE` matches `## YYYY-MM-DDTHH:MM:SSZ — Closure` or the
  legacy `## YYYY-MM-DD — Closure` at a line start. The summary names the
  latest heading (`'## 2026-10-30T23:59:00Z — Closure' present`), and a miss
  reads `no '## YYYY-MM-DDTHH:MM:SSZ — Closure' section`. Why this option and
  not the others is in log.md.
- **The line anchor carries more weight now.** Dates no longer filter
  anything, so the anchor is the only thing stopping attest's own block,
  whose result line quotes a closure heading, from passing the next run.
  The regression test pins that a failed run's block does not satisfy the
  check, and neither does a passing run's.
- **`today` stays in `_run_derived_check`'s signature**, now read by no
  check. Four deck reproducers pass it, two of them on open decision-gated
  cards that a re-check would re-run. Removing it would crash them with a
  `TypeError`, and that exit 1 reads as "defect fires".
- **Docs.** `Skill(finish-card)` Step 4 now says the check takes the heading
  whatever day it names. Before, it said "date-prefix-matches". `_cmd_attest`'s
  docstring dropped two claims that do not hold. One was that a late attest
  on a closed card fails this check. The other was that a bare
  `## Closure verification` header satisfies it, which was never true.

Not changed: the em-dash separator stays strict. Whether an ASCII-hyphen
heading should pass is the open decision on
[attest-closure-marker-check-rejects-ascii-hyphen-headings-as-missing](../attest-closure-marker-check-rejects-ascii-hyphen-headings-as-missing/).

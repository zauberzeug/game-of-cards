---
title: backfill-terminal-closed-at-stamps-latest-edit-date-as-closure-date
summary: "scripts/backfill_terminal_closed_at.py derives closed_at from the most recent commit touching the card's README (git log -1), but closed cards are routinely edited after closure (cross-reference rewrites, forward pointers, quality passes — closure is not frozenness), so --apply writes the latest edit date, not the closure date, silently corrupting the record axis that --closed-since, standup, and retrospective velocity consume."
status: open
stage: null
contribution: medium
created: "2026-07-24T01:57:31Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py lands (temp git repo: closure commit at T1, later cross-reference edit at T2, closed_at nulled) and exits non-zero while --apply writes T2 — drop the unverified tag when it lands
  - [x] EMPIRICAL: error rate of the heuristic against this repo's real terminal cards is re-measured and recorded in log.md
  - [ ] MECHANICAL: the chosen heuristic (per the decision below) replaces latest_readme_commit_iso, with the dry-run output showing which commit it picked
  - [ ] MECHANICAL: uv run goc validate passes
---

# backfill-terminal-closed-at-stamps-latest-edit-date-as-closure-date

## Summary

`scripts/backfill_terminal_closed_at.py` derives `closed_at` from the most
recent commit touching the card's README (`git log -1`), but closed cards are
routinely edited after closure (cross-reference rewrites from `goc move`,
forward pointers, quality passes — "closure is not frozenness" is an
always-loaded deck rule), so `--apply` writes the latest *edit* date, not the
*closure* date, silently corrupting the record axis that `--closed-since`,
standup, and retrospective velocity consume.

## Location

`scripts/backfill_terminal_closed_at.py:43-61` (`latest_readme_commit_iso`),
consumed at line 85 via `mutate_frontmatter_field(text, "closed_at", ts)`.

## Hypothesis (confirmed 2026-11-09 — see § Empirical evidence)

```python
out = subprocess.check_output(
    ["git", "log", "-1", "--format=%aI", "--", str(rel)],   # backfill_terminal_closed_at.py:52
    cwd=ROOT,
```

The script's own docstring states the intent: "asks git for the most recent
commit touching the card's README and writes that timestamp". That equates
"last edited" with "closed", which the methodology itself contradicts —
closed cards keep receiving edits.

## Empirical evidence

[`reproduce.py`](reproduce.py) builds a throwaway git repo with one card
filed at T0, closed (`status: superseded`) at T1 and given a later
cross-reference edit at T2, `closed_at` null throughout. It runs a run-time
copy of the current script with `--apply` there. On main at `92f8bb55`
(2026-11-09) it exits 1:

```text
$ backfill_terminal_closed_at.py --apply   (exit 0)
  applied: old-card  closed_at: 2026-03-01T00:00:00Z  (status: superseded)

closure commit (T1) : 2026-02-01T00:00:00Z
latest edit    (T2) : 2026-03-01T00:00:00Z
closed_at written   : 2026-03-01T00:00:00Z

DEFECT PRESENT: --apply stamped the latest README edit (T2), not the closure (T1).
```

Error rate on this repo's own terminal cards, re-measured 2026-11-09: the
closure commit is the newest commit after which the card's terminal `status:`
line is present; the heuristic's pick is `git log -1` on the README. The two
fall on different days for 7 of 8 `disproved` and 4 of 6 `superseded` cards,
11 of 14 (79%), the script's whole population. The same heuristic would
misdate 266 of 620 `done` cards (43%), which the script does not target. Full
table in `log.md`.

A hunter-run measurement against this repo's real deck reported that of 14
disproved/superseded cards with a recorded `closed_at`, 11 (79%) have a
latest-README-commit date that differs from the true closure date — e.g.
[decide-card-body-format-readme-vs-html-vs-flexible](../decide-card-body-format-readme-vs-html-vs-flexible/)
closed 2026-05-09 but last touched 2026-05-29 (+20 days). Re-measured on
2026-11-09 with the same result, and reproduced end-to-end — see § Empirical
evidence.

## Why it matters

The script is the documented migration path for any legacy consumer deck
adopting the symmetric terminal-`closed_at` validator (commissioned by the
closed card
[record-closure-date-for-disproved-and-superseded-cards](../record-closure-date-for-disproved-and-superseded-cards/)).
Its risk note anticipated only "multiple status-flip commits", not routine
post-closure churn; the measured 79% error rate is new evidence the heuristic
is wrong in the *common* case, not an edge. `--apply` is one flag away and the
corruption is silent (a plausible-looking timestamp). Mitigated by the dry-run
default and by this repo's own deck already being backfilled.

## Falsification recipe

Temp git repo: commit a card's closure (status `superseded`) at T1; commit a
later README edit at T2; set `closed_at: null`; run the script `--apply`. The
claim is falsified if the written `closed_at` is T1.

## Decision required

Which heuristic should replace latest-commit? Credible options: (1) earliest
commit whose diff introduces the terminal `status:` line (`git log -S` /
`-G` on the status field, last-flip wins); (2) latest commit that *changed*
the status field rather than any README edit; (3) keep the current heuristic
but demote `--apply` output to per-card review with the candidate commit
subject shown. Option 1/2 need care with cards whose status flipped multiple
times; the right pick defines what the DoD's reproduce.py asserts.

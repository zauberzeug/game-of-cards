---
title: set-cadence-silently-half-retunes-workflows-with-two-cron-schedule-lines
summary: "FIXED: `retune()` in scripts/set_cadence.py substituted with `count=1`, so its \"expected exactly one `- cron:` line\" guard could never see a count above 1 — a workflow with two `- cron:` schedule entries was silently half-retuned (first line rewritten, second kept firing the autonomous agent at the stale cadence) and `--show` reported only the first match. retune() now counts every match and refuses multi-schedule workflows before writing; --show reports all schedule lines."
status: done
stage: null
contribution: low
created: "2026-07-06T01:20:23Z"
closed_at: "2026-07-08T00:59:21Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py lands and exits non-zero on current code (two-cron workflow retunes without error, second schedule untouched), zero after the fix; drop the `unverified` tag when it lands
  - [x] TDD: `retune()` on a workflow with two `- cron:` lines either raises the multiple-schedules error or rewrites all managed schedule lines; `--show` no longer hides schedules after the first match
worker: {who: "claude[bot]", where: main}
---

# set-cadence-silently-half-retunes-workflows-with-two-cron-schedule-lines

> ✅ Verified and fixed 2026-07-08. `reproduce.py` in this directory
> exercised the defect (exit 1 pre-fix, exit 0 post-fix); regression
> tests live in `tests/test_set_cadence.py`.

## The defect (confirmed)

`retune()` in `scripts/set_cadence.py` substituted both the `- cron:`
line and the `# cadence:` marker with `count=1`, so `re.subn` could
never return a count above 1 and the "expected exactly one" guards were
unreachable dead code for the multiple-match case (they could only fire
on zero matches). A workflow file carrying two `- cron:` entries
(GitHub Actions supports multiple schedules) was silently half-retuned:
the first line was rewritten to the new cadence, the second kept
launching the deck-mutating autonomous workflow at the old cadence, and
the tool reported success. `current_cadence()` used `.search`, so
`--show` reported only the first schedule — hiding the stale line.

Secondary text-rot in the same file: the argparse `epilog` still
documented interval specs as "`<N>h (1,2,3,4,6,8,12)` or `1d/24h`",
omitting the `<N>d` and `1w` specs the tool accepts.

## The fix

- `retune()` now substitutes without `count=1`, so the guards observe
  the true match count and raise the multiple-schedules `ValueError`
  before any write (the file is only written after both guards pass —
  a refused workflow is left byte-identical). Rejecting rather than
  rewriting all lines was chosen because the tool's model is one
  managed schedule per workflow; rewriting N lines to the same cron
  would collapse a deliberate second slot into duplicates.
- `current_cadence()` uses `findall` and joins every `- cron:` /
  `# cadence:` match, so `--show` reports all schedule lines.
- The `epilog` now lists the full spec set: `<N>h (1,2,3,4,6,8,12)`,
  `24h`, `<N>d (<=31)`, `1w`.

Regression coverage: `tests/test_set_cadence.py` —
`test_two_cron_lines_rejected_and_file_untouched`,
`test_duplicate_cadence_marker_rejected`,
`test_show_reports_every_schedule_line`.

## Why it mattered

`scripts/set_cadence.py` is what the `tune-cadence` skill runs to retune
`pull-card.yml` / `audit-deck.yml` / `refine-deck.yml`. If a maintainer
added a second schedule entry (e.g. a weekend slot) and later retuned,
the tool claimed the cadence was set while a stale schedule kept firing
cloud agents — silent wrong-cadence state on the workflows that mutate
this deck autonomously. Blast radius is this repo's dev tooling only,
hence `contribution: low`.

## Distinct from existing cards

- [set-cadence-day-interval-over-31-emits-monthly-only-cron](../set-cadence-day-interval-over-31-emits-monthly-only-cron/)
  (done) — interval validation, not schedule-line counting.
- [support-multi-day-intervals-and-slow-the-autonomous-cadence](../support-multi-day-intervals-and-slow-the-autonomous-cadence/) /
  [support-weekly-interval-and-slow-the-autonomous-cadence](../support-weekly-interval-and-slow-the-autonomous-cadence/)
  (done) — feature cards that added the specs the epilog under-documented.

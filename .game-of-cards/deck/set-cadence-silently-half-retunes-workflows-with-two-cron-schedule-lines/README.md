---
title: set-cadence-silently-half-retunes-workflows-with-two-cron-schedule-lines
summary: "`retune()` in scripts/set_cadence.py substitutes with `count=1`, so its \"expected exactly one `- cron:` line\" guard can never see a count above 1 (dead code); a workflow with two `- cron:` schedule entries is silently half-retuned — the first line is rewritten while the second keeps firing the autonomous agent at the stale cadence, and `--show` reports only the first match. Parked unverified pending a reproduce.py."
status: open
stage: null
contribution: low
created: "2026-07-06T01:20:23Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, unverified]
definition_of_done: |
  - [ ] TDD: reproduce.py lands and exits non-zero on current code (two-cron workflow retunes without error, second schedule untouched), zero after the fix; drop the `unverified` tag when it lands
  - [ ] TDD: `retune()` on a workflow with two `- cron:` lines either raises the multiple-schedules error or rewrites all managed schedule lines; `--show` no longer hides schedules after the first match
---

# set-cadence-silently-half-retunes-workflows-with-two-cron-schedule-lines

Parked `unverified`: surfaced and empirically exercised by the audit-round
hunter agent, but no committed `reproduce.py` this round. Hypothesis and
falsification recipe below.

## Hypothesis

`scripts/set_cadence.py:148-152` (`retune()`):

```python
text2, n_cron = _CRON_RE.subn(lambda _m: new_cron_line, text, count=1)
if n_cron != 1:
    raise ValueError(
        f"{filename}: expected exactly one `- cron:` line, found {n_cron}"
    )
```

With `count=1`, `re.subn` never returns `n_cron > 1`, so the "exactly one"
guard is unreachable dead code for the multiple-match case (it can only
fire on zero matches). The same `count=1` pattern applies to the
`# cadence:` marker at lines 153-158, and `current_cadence()`
(lines ~175-181) uses `.search`, reporting only the first schedule in
`--show`. A workflow file carrying two `- cron:` entries (GitHub Actions
supports multiple schedules) is silently half-retuned: the first line is
rewritten to the new cadence, the second keeps launching the deck-mutating
autonomous workflow at the old cadence, and the tool reports success.

Secondary text-rot in the same file: the argparse `epilog` (line ~202)
still documents interval specs as "`<N>h (1,2,3,4,6,8,12)` or `1d/24h`",
omitting the `<N>d` and `1w` specs the tool accepts (module docstring
lines 19-24, `interval_to_cron`).

## Why it matters

`scripts/set_cadence.py` is what the `tune-cadence` skill runs to retune
`pull-card.yml` / `audit-deck.yml` / `refine-deck.yml`. If a maintainer
adds a second schedule entry (e.g. a weekend slot) and later retunes, the
tool claims the cadence is set while a stale schedule keeps firing cloud
agents — silent wrong-cadence state on the workflows that mutate this
deck autonomously. Blast radius is this repo's dev tooling only, hence
`contribution: low`.

## Falsification recipe

Write a scratch `pull-card.yml` containing a managed `# cadence:` comment
and *two* `- cron:` lines; call `retune(root, "pull", "4h")`. The
hypothesis is falsified if it raises the multiple-schedules `ValueError`;
confirmed if it returns success with only the first cron rewritten. The
hunter's in-round check observed: `retune` returned `('13 */4 * * *',
True)` with no error and left the second line (`13 9 * * 6,0`) untouched.

## Distinct from existing cards

- [set-cadence-day-interval-over-31-emits-monthly-only-cron](../set-cadence-day-interval-over-31-emits-monthly-only-cron/)
  (done) — interval validation, not schedule-line counting.
- [support-multi-day-intervals-and-slow-the-autonomous-cadence](../support-multi-day-intervals-and-slow-the-autonomous-cadence/) /
  [support-weekly-interval-and-slow-the-autonomous-cadence](../support-weekly-interval-and-slow-the-autonomous-cadence/)
  (done) — feature cards that added the specs the epilog now under-documents.

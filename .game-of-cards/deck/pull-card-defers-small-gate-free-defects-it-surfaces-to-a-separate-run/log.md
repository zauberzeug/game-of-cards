## 2026-05-30 — filed

Filed from a commit-history review: the last ~200 commits showed a heavy
file-then-fix-minutes-later pattern. Measured the deck and confirmed
median time-to-close = 6.3 min, 60% < 10 min, authored fix ~48 lines / 2
files, filing rate 28–53/day vs audit cron 1/day (so pull-card sessions
do ~97% of the filing as a side effect of their work).

Decision: Rodja chose **"fix-through, keep the card"** from four options
(fix-through-keep-card / inline-fix-no-card / overhead-only /
analysis-defer). Keep the card (record axis + TDD test are load-bearing,
this repo dogfoods goc's record); cut the wasteful *separate run* by
letting the filing session close small/mechanical/gate-free findings
in place. Threshold-gated so subtle/cross-cutting work still gets a
fresh-context second look. `audit-deck` stays flag-don't-fix.

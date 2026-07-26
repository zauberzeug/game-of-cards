## 2026-06-21 — built set-cadence tooling and applied the faster cadence

- Added `scripts/set_cadence.py` (stdlib only): `--show` query plus
  `--pull/--audit/--refine` interval rewrite of the `- cron:` line and the
  managed `# cadence:` comment; fixed minute offsets (pull :00, audit :15,
  refine :45); rejects non-divisor hour intervals and multi-day specs.
- Added `tests/test_set_cadence.py` (interval→cron mapping, idempotence, --show).
- Added `.github/workflows/refine-deck.yml` (Skill(refine-deck), opus, bypassPermissions).
- Ran the script to apply: pull `0 * * * *`, audit `15 */3 * * *`,
  refine `45 */3 * * *`; collapsed the old schedule comments to the
  `# cadence:` marker and dropped "daily" from audit-deck's header.
- Added repo-local Claude skill `.claude/skills/tune-cadence/SKILL.md`,
  preserved in `scripts/sync_plugin_assets.py` so the dogfood sync keeps it.
- Reverses the cadence from `run-pull-card-daily-and-audit-deck-weekly`
  (amended there with a forward pointer); `MAX_ITERATIONS` cap untouched.
- Verification: test_set_cadence + `sync --check` + `goc validate` green;
  full suite 486/487 (sole failure is the interactive-rebase guard test the
  sandbox cannot set up — it shells out to `git rebase -i`; passes in CI).

## 2026-06-21 — Closure

Closed: all 6 DoD items met. `scripts/set_cadence.py` + the `tune-cadence`
repo-local skill + `refine-deck.yml` shipped; cadence applied (pull-card
hourly, audit-deck + refine-deck every 3h) and verified via `--show`, an
idempotent re-run, `goc validate`, `sync --check`, and
`test_set_cadence`. Reverses `run-pull-card-daily-and-audit-deck-weekly`
(amended there with a forward pointer); `MAX_ITERATIONS` cap untouched.
The only regression-suite failure is the sandbox-only interactive-rebase
guard test (`git rebase -i` unsupported here; passes in CI). Pending:
push to `main` so the new cron takes effect (scheduled workflows run from
the default branch).

## Closure verification (2026-06-21T05:25:13Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-06-21 — Closure' present

## 2026-06-21 — pull-card moved off :00

Follow-up: pull-card's minute offset moved `:00` → `:13` to dodge GitHub's
congested top-of-hour schedule slot (this repo's scheduled runs dispatch
~85–90 min late, worst at `:00`). The `WORKFLOWS` table in
`scripts/set_cadence.py` now bakes in pull `:13`. See
`shift-pull-card-off-the-congested-top-of-hour-cron-slot`.

## 2026-06-21 — multi-day intervals now supported

Follow-up: the "multi-day intervals rejected" behavior recorded above was
reversed. `set_cadence.py` now maps `<N>d` (N≥2) to a day-of-month `*/N`
cron step (roughly every N days, realigning at month boundaries). See
`support-multi-day-intervals-and-slow-the-autonomous-cadence`.

## 2026-07-26T05:59:56Z — Later evidence: the out-of-scope list grew a third member

`--effort` was added to all three workflows' `claude_args` blocks by
[run-autonomous-agent-workflows-at-max-effort](../run-autonomous-agent-workflows-at-max-effort/)
(commit `ef509b45`), joining `--model`, `--permission-mode`, and
`--max-turns` as hand-synced settings. This card single-sourced the cron line
(managed `# cadence:` comment, `--show`, multi-schedule guard) and explicitly
deferred the rest; that deferral is now where four un-guarded settings live.

Two facts worth recording for whoever revisits it:

- A naive "all three files must match" guard would be wrong. `--permission-mode`,
  `--model`, and `--effort` are fleet-wide and must agree; `--max-turns`
  deliberately differs (120 pull-card, 200 audit-deck/refine-deck). A guard has
  to distinguish the two classes.
- No drift has occurred. Model values were checked across every commit touching
  these files since 2026-05-09 and have never diverged — `refine-deck.yml` was
  absent before `870bce3b` and was created already matching the fleet.

Deliberately **not** filed as its own card: the exposure is small, no instance
has been observed, and the floating `opus` alias reduced the edit frequency
that would trigger it. Captured here so the decision is discoverable instead of
being re-litigated on the next `claude_args` change.

No status change: this card stays `done`.

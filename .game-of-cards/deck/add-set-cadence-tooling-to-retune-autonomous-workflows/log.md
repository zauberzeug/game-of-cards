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

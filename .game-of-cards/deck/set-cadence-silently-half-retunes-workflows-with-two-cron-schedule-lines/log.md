# Log

## 2026-07-08 — verified, fixed, closed

Pulled autonomously. `reproduce.py` committed and run against the
pre-fix code: `retune(repo, "pull", "4h")` on a two-schedule workflow
returned `('13 */4 * * *', True)` with no error, left the second
schedule (`13 9 * * 6,0`) at the stale cadence, and `--show` reported
only the first line — hypothesis confirmed exactly as the audit-round
hunter observed, exit 1.

Fix in `scripts/set_cadence.py`: removed `count=1` from both `subn`
calls in `retune()` so the "expected exactly one" guards see the true
match count and refuse multi-schedule workflows before writing;
`current_cadence()` switched from `.search` to `findall` so `--show`
reports every schedule line; argparse `epilog` updated to list the
`<N>d` and `1w` specs. Chose reject-over-rewrite-all: the tool manages
a single schedule per workflow, and rewriting N lines to one cron would
collapse a deliberate second slot into duplicates.

Post-fix: `reproduce.py` exits 0; three new regression tests in
`tests/test_set_cadence.py`; full suite 702 tests OK. `unverified` tag
dropped with the reproduce landing.

## 2026-07-08T00:00:00Z — Closure

- **What changed**: `scripts/set_cadence.py:148-176` — dropped `count=1`
  from both `subn` calls in `retune()` so the "expected exactly one"
  guards refuse multi-schedule workflows before writing;
  `current_cadence()` now `findall`s every `- cron:` / `# cadence:`
  match so `--show` reports all schedule lines; epilog lists `<N>d`/`1w`.
- **Verification**: `reproduce.py` exit 1 pre-fix, exit 0 post-fix;
  three new tests in `tests/test_set_cadence.py`.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a (repo-local dev tooling only).
- **Tests**: 702 passed / 0 failed.

## Closure verification (2026-07-08T00:59:15Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 2/2 ticked
- [x] log-md-closure-entry — '## 2026-07-08 — Closure' present

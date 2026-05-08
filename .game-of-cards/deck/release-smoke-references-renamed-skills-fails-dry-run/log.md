## 2026-05-08 — Closure

Renamed three external callers in lockstep:

- `.github/workflows/release.yml` — Path A and Path B prompts, `--allowedTools`, comments, and step names now reference `Skill(audit-deck)` / `Skill(kickoff)`.
- `scripts/smoke_release.sh` — local mirror updated identically.
- `goc.md` — autonomous-loop sentence now says "audit the deck" / `audit-deck` skill.

Verified by re-triggering `release.yml` with `dry_run=true` against commit
`5353dc4`: run **25560598958** finished `success` (build green; smoke job
green with both Path A and Path B passing; publish correctly skipped).
The earlier failing run on the same workflow + prior commit was
**25560080412** (Path B `Assert` failed because the LLM had no fallback
when the named skills did not resolve).

Path A's general `Bash` allowance still hides skill-name typos behind a
direct `goc install` fallback — Path B remains the canary. Out-of-scope
follow-up about a static-analysis tripwire for skill identifiers in CI
workflows is noted in the README; not filed because the dry-run on every
release-relevant change already exercises the paths.

## Closure verification (2026-05-08)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 done
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-05-08 — Closure' present

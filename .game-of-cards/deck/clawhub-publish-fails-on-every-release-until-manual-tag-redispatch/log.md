# Log

## 2026-06-26 — filed + claimed

Surfaced while cutting the v0.0.25 release: PyPI + npm published from the
from-`main` dispatch, but the ClawHub leg failed with `Trusted publish
source commit must match the verified GitHub SHA`. v0.0.25 shipped to
ClawHub only after a manual `gh workflow run release.yml --ref v0.0.25`
re-dispatch (run 28223068119, which published ClawHub successfully).

Root cause confirmed (not a ClawHub-side change): the commit guard
predates v0.0.16; our own `ref:tag` fix `3167525` (landed just after
v0.0.24) made the ClawHub leg publish the post-rewrite tag commit, which
differs from the OIDC dispatch SHA (pre-rewrite `main` HEAD). v0.0.25 is
the first release to exercise that wiring. Verified against ClawHub's
server source (`resolveTrustedPublishSource`) and the local git timeline.

## 2026-06-27 — implemented + merged (PR #5)

Fix: `release.yml` self-dispatches a `clawhub_only` run on the
freshly-pushed tag (`redispatch-clawhub` job, default `GITHUB_TOKEN` +
`actions: write` — no PAT, no ClawHub reconfiguration). `publish-clawhub`
now runs only in `tag` mode; `clawhub_only` skips smoke/pypi/npm; the
tag-mode run does not re-dispatch (no loop). Tests extended; AGENTS.md +
CONTRIBUTING.md release sections rewritten in place.

Merged to `main` via PR #5 (rebased: card `4625211`, fix `a1ecb2f`). CI
green across Python 3.10–3.13; `actionlint` clean on `release.yml`.

**Kept active (not closed) — verification gap:** the dispatch-from-tag
mechanism that clears ClawHub's commit guard is empirically proven (the
v0.0.25 recovery run), and the `clawhub_only` gating is unit-tested, but
the *automatic* re-dispatch firing end-to-end can only be confirmed by a
real release. Close after the next `gh workflow run release.yml -f
version=X.Y.Z` publishes all three registries with no manual second step.

## 2026-07-01T05:13:28Z — Closure

The verification gap is closed by the **v0.0.26** release. No code
changed in this closure — the fix landed in PR #5 (`a1ecb2f`); this
entry records the empirical end-to-end confirmation the previous entry
was waiting for.

- **What changed**: nothing new — closure lands on `release.yml`'s
  `redispatch-clawhub` mechanism (PR #5). v0.0.26 was cut with a single
  `gh workflow run release.yml -f version=0.0.26`.
- **Verification**: from-main run `28494572761` green — build → smoke →
  pypi + npm + `redispatch-clawhub`, with `publish-clawhub` **skipped**
  (`mode == release`). It auto-dispatched tag run `28494689798`
  (`clawhub_only=true`, `mode == tag`), which skipped smoke/pypi/npm and
  published **ClawHub green** (no manual step; no re-dispatch loop).
  Registries independently confirmed live at `0.0.26`: PyPI + npm
  registry JSON, ClawHub via the green publish job. v0.0.25 by contrast
  needed a hand-run `--ref` re-dispatch that then collided with npm.
- **Audit**: PASS — no rubric configured (finish-card hook empty);
  release-infra fix, verified end-to-end by the real v0.0.26 dispatch.
- **Tests**: `tests/test_release_workflow_clawhub_source_ref.py` — 6
  passed / 0 failed. `actionlint release.yml`: actionlint core clean (as
  at PR #5); its optional shellcheck integration reports 3 pre-existing
  style/info findings (SC2001/SC2086 at L269/L273/L492) in the
  version-tripwire and Path-A steps, last touched 2026-05, unrelated to
  the ClawHub wiring — left as-is (L269's unquoted `$tracked` is an
  intentional word-split; "fixing" it would break the tripwire).
- **Project impact**: closes the last release-flow gap — one human
  dispatch now publishes PyPI + npm + ClawHub unattended.

## Closure verification (2026-07-01T05:14:10Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-07-01 — Closure' present

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

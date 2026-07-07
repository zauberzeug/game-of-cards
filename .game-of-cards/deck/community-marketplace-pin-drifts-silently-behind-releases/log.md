
## 2026-07-05 — workflow authored, awaiting first live runs

Implemented `.github/workflows/marketplace-pin-check.yml`. Decision logic
dry-run against live GitHub data (v0.0.26 → `d19aa09a`, pin `4e4c5a1`,
compare → `behind`; self-compare → `identical`; release age 108h > 48h
grace). Card stays **active** until the scheduled run has demonstrated the
issue-create/update/close lifecycle in CI.

## 2026-07-07 — full lifecycle verified; empty-tag crash fixed

First scheduled run (28787589943, 2026-07-06) flagged the stale pin and
opened tracking issue #8. A manual `workflow_dispatch` (28834156281)
proved update-in-place: #8 edited, still exactly one labelled issue.
Remaining paths exercised by running the exact `run:` block locally with
env overrides and a temporary `marketplace-pin-test` label: auto-close
(mocked fresh pin → closed test issue #9), grace window (clock shim →
"1h old, not flagging", exit 0), delisted entry (explicit flag). The
no-release path crashed (grep with no matching tags fails the pipeline
under `set -euo pipefail` before the empty-tag guard) — fixed by
appending `|| true` to the tag-resolution pipeline; re-tested clean.
Test artifacts cleaned up: label deleted, #9 retitled/commented as a
verification artifact. Real tracker #8 stays open until the marketplace
re-pin lands — that is the issue's job, not this card's.

## 2026-07-07T01:15:00Z — Closure

- **What changed**: .github/workflows/marketplace-pin-check.yml:58-63 — `|| true` on the tag-resolution pipeline so tagless repos hit the clean "No release tag yet" exit instead of dying under `set -euo pipefail`; all six DoD paths verified (two real CI runs + four controlled local runs of the extracted script).
- **Verification**: CI runs 28787589943 (create, issue #8) and 28834156281 (update-in-place, still exactly one labelled issue); local: auto-close (test issue #9), grace window (1h < 48h → no flag), no-release exit 0, delisted-entry explicit flag.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: distribution chain now monitored end-to-end; issue #8 tracks the live re-pin.
- **Tests**: n/a (workflow-only change; regression suite untouched)

## Closure verification (2026-07-07T01:09:14Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-07-07 — Closure' present

## 2026-07-07T01:20:00Z — Post-close amendment

The closure entry above records the `|| true` no-release fix as part of
this card's diff, but the push was rejected: the autonomous bot's App
token lacks the `workflows` permission and cannot update
`.github/workflows/marketplace-pin-check.yml`. The workflow edit was
reverted from this card's commit; the verified patch and its
application are re-scoped to
[`marketplace-pin-check-crashes-on-repos-without-version-tags`](../marketplace-pin-check-crashes-on-repos-without-version-tags/)
(gate `session` — needs a human with workflow-push rights). DoD item 5
and the README verification section were rewritten accordingly. All
other verified paths (drift detection, issue create/update/close, grace
window, delisted entry) are live on main's committed workflow, so the
closure stands.

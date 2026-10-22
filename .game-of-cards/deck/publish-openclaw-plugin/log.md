## 2026-05-09 — Grooming pass

- Added "## What is OpenClaw" identity-anchor section. OpenClaw is an open-source personal AI assistant at <https://github.com/openclaw/openclaw>, Node/npm-distributed, with the public skills registry ClawHub at <https://clawhub.ai>. Identity verified 2026-05-09 via WebSearch across multiple independent domains plus WebFetch of upstream docs (full anchor on `provide-openclaw-plugin-for-skills-and-hooks`).
- Tightened DoD around ClawHub publication primarily and npm secondarily.

## 2026-05-09 — Distribution decided; gate lowered

- Distribution channels locked in via the decisions on `provide-openclaw-plugin-for-skills-and-hooks`: ClawHub + npm. The npm package name is `game-of-cards` (verified available 2026-05-09; `goc` is squatted by a 0.0.0 placeholder, so the longer name is both the clean choice and matches the PyPI artifact name).
- DoD restructured: ClawHub and npm are now both required (not optional); release workflow must cover both; smoke test must verify both channels.
- `human_gate: session → none`. Card is mechanical follow-up to `provide-openclaw-plugin-for-skills-and-hooks`; nothing here needs human judgment.

## 2026-05-09 — Consumer prerequisite updated to match the bundling pivot

`provide-openclaw-plugin-for-skills-and-hooks` pivoted later the same day from "shell out + `pipx install game-of-cards`" to "vendor the goc engine in the npm payload + `bin/goc` wrapper" (symmetric to the Claude plugin). Distribution channels (ClawHub + npm) and npm package name (`game-of-cards`) are unchanged by the pivot — only the artifact's internal shape and the consumer-side prerequisite changed.

DoD updated: the consumer-side prerequisite now reads `python3` + `uv` (matching the Claude plugin) instead of `python3` + `pipx` + `pipx install game-of-cards`. No other DoD items affected.

## 2026-07-13 — Deck hygiene pass

Stale-open review (60d+ without log activity): lead still real — the openclaw-plugin payload exists in-tree and 7 prereq children are wired; publish itself has not happened. Awaiting a human session per `human_gate: session`; no status change.

## 2026-05-06: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Blocked by `provide-openclaw-plugin-for-skills-and-hooks` which is parked at gate:session pending human decisions about the wrapper pattern and external publishing accounts.

This card requires: (1) the parent card to land, (2) ClawHub and npm publishing credentials available to the executor, (3) human-verified smoke test. All three items require human action. Raising gate to session until the parent is resolved.


## 2026-10-22T05:10:47Z: decision recorded

Close as done: both channels are live (npm game-of-cards 0.0.7-0.0.27, ClawHub via the OIDC release leg); strike the per-channel smoke item — The maintainer approved the retirement in a human session on 2026-10-22 after a code and registry check showed every publication item met; the 2026-07-13 hygiene note claiming publish never happened was wrong. Gate session → none.

## 2026-10-22T05:11:18Z — Closure

- **What changed**: no code — the card is retired against the registries. Recorded the chosen package id (`game-of-cards` on both ClawHub and npm) and the evidence in the README's new "## Outcome" section; `openclaw-plugin/README.md` § Install drops the stale "Once published to ClawHub:" framing.
- **Verification**: npm registry lists 21 versions, 0.0.7 (2026-05-10) to 0.0.27 (2026-07-14); release run 29305647155 on `v0.0.27` reports `publish-clawhub / publish: success`; `uv run goc validate` exit 0.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: the deck stops advertising an unpublished OpenClaw plugin; `support-external-game-of-cards-state-location` loses its last open prerequisite.
- **Tests**: no code touched; the full suite runs at the end of this batch.
- **Struck**: DoD 7 (per-channel smoke) — no such step exists and the registries plus a production deployment verify publication.
- **Correction**: the 2026-07-13 hygiene entry ("publish itself has not happened") was wrong; npm had carried the package since 2026-05-10.

## Closure verification (2026-10-22T05:11:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 7 closed
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-10-22 — Closure' present

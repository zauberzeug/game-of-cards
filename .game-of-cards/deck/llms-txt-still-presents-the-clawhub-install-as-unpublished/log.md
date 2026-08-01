## 2026-08-01T05:40:13Z — Closure

- **What changed**: `site/llms.txt:78,86` — the `## Install (OpenClaw)`
  section stops gating a live channel behind a pending publish. "Once the
  plugin is published, install via ClawHub:" → "Install via ClawHub:"; the
  "Until publish lands (tracked under publish-openclaw-plugin), build from
  source…" sentence → "To run against an unreleased checkout instead, build
  from this repo's plugin payload at …", which keeps the useful pointer,
  drops the false premise, and removes a deck-internal card slug from a
  public document.
- **Guard added**: `tests/test_llms_txt_install_channels.py` — three checks:
  no listed channel is described as pending publish; the ClawHub install
  command in llms.txt still matches README.md / ABOUT.md / goc.md /
  site/index.html; llms.txt cites no deck card slug (shipped skill names
  exempted, since llms.txt legitimately names `create-card` / `pull-card` /
  `finish-card` as product vocabulary).
- **Verification**: `reproduce.py` exit 1 → exit 0 (`[OK] site/llms.txt
  carries no pending-publish caveat` / `4/4 sibling surfaces agree the
  ClawHub install is live`). The new guard is non-vacuous — replayed against
  `git show HEAD:site/llms.txt` it detects both markers and the
  `publish-openclaw-plugin` citation, so it fails on the pre-fix content.
- **Live-registry evidence**: `https://clawhub.ai/api/v1/packages/game-of-cards`
  returns `name: game-of-cards`, `latestVersion: 0.0.27`, created
  2026-05-10T05:45:04Z — the current release, ten patch releases after the
  publish landed. npm agrees (`registry.npmjs.org/game-of-cards`,
  `latest: 0.0.27`, 21 versions).
- **Audit**: no rubric configured; mechanical fix.
- **Forward pointer**: `add-openclaw-install-section-to-llms-txt` (closed
  2026-05-09) gained an `## After closure` section and a log entry. Its own
  "Notes" required the section to be "honest about state" and to flip to the
  registry install post-publish; nothing owned that transition, which is the
  whole cause. Not re-opened — its DoD was satisfied as written on the day it
  closed.
- **Out of scope**: `publish-openclaw-plugin` is itself stale (`open`,
  `human_gate: session`, 0/8 DoD, all seven `advanced_by` prerequisites
  closed). Reconciling it is deck hygiene behind a human gate and does not
  block this fix.
- **Tests**: 878 passed / 0 failed (`uv run python -m unittest discover -s
  tests`); `uv run goc validate` clean; `uv run python
  scripts/check_card_language.py --check` clean (695 cards).

## Closure verification (2026-08-01T05:40:49Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-01 — Closure' present

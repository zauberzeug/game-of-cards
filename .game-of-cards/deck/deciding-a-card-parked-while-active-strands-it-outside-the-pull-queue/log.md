## 2026-10-01T04:53:10Z — Closure

- **What changed**: `goc/engine.py:6983`, `:7001` — `goc decide` returns a card parked while `active` to `open` in the same write and `decide:` commit as the gate flip. It prints `<title>: active → open`, journals `Status active → open`, and its `Next:` line (`:7042-7046`) adds `goc status <title> active` for a session that wants to keep the card. `worker` is kept, as `goc status <title> open` keeps it. Cards parked while `open` and terminal cards are unchanged. `decide-card/SKILL.md`, `decide-card/reference.md`, `deck/SKILL.md` and `deck/reference.md` now describe the release, and the mirrors and the OpenClaw port were regenerated.
- **Verification**: `reproduce.py` exits 1 on the pre-fix engine (`active` / `none`, absent from `goc --ready` and from pull-card.yml's launch query, present under `--status active`) and exits 0 on the fix (`open` / `none`, present in both, absent from `--status active`). `tests/test_decide_releases_parked_active_claim.py` fails on the pre-fix engine (checked in a throwaway worktree at HEAD) and passes on the fix.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1206 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`); `goc validate`, both card guards, `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` clean.
- **Bundled with**: none

Took the card's recommended direction. A same-session decide-then-implement
flow is real: `openclaw-plugin-skills-force-repeated-reads-every-session`
was approved by the maintainer and implemented in one session. That flow now
re-claims with the command the `Next:` line names, instead of keeping a
claim nobody can tell from a stranded one. The held draft
`escalate-repeatedly-auto-released-cards-without-an-attempt-counter` hooks
`_cmd_status`'s release. The release added here lives in `_cmd_decide`,
is a decided handoff, and must not arm that ladder; the README's Fix section
records this.

## Closure verification (2026-10-01T04:53:14Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-01 — Closure' present

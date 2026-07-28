# log — retrospective-status-done-queries-hide-disproved-and-superseded-closures

## 2026-07-26T13:02:00Z — Closure

- **What changed**: `goc/templates/skills/retrospective/SKILL.md:17,39,119` —
  the three closure-gathering queries now span every terminal status
  (`--closed-since 90d` for the Context block; `--status all` plus a
  `TERMINAL = {'done','disproved','superseded'}` filter for Steps 1 and 5),
  Step 1 emits each card's `status` so Step 3's disproved/superseded bullet
  is answerable, and `goc/templates/skills/deck/SKILL.md`'s closed-cards
  verb row moved from the `done`-only `--since` form to `--closed-since 7d`.
- **Verification**: `reproduce.py` exit 0 — both prescribed queries reach
  3/3 terminal closures on the probe deck; the same probe pointed at
  `HEAD`'s pre-fix body reports `1/3 closures · HIDES probe-disproved-card,
  probe-superseded-card` and exits 1. On this deck the retrospective's 30-day
  velocity line now reads 69 (was 67); 13 of 495 closures were previously
  invisible. All three assertions in `tests/test_retrospective_closure_scope.py`
  fail against the pre-fix content and pass against the shipped content.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is an unauthored stub). Not purely mechanical, though: the closure binds the
  engine's own `TERMINAL_STATUSES` comment (`goc/engine.py:2310-2316`,
  "'terminal' is a semantic subset") as the authority for what counts as a
  closure, and the coupling test pins the skill body's hand-listed set to it.
- **Project impact**: n/a
- **Tests**: 786 passed / 0 failed / 0 xfailed. `scripts/sync_plugin_assets.py
  --check` and `scripts/port_skills_to_openclaw.py --check` both green after
  re-syncing the five mirrors (8 files via the asset sync, the OpenClaw skill
  via the porter).
- **Surfaced, not fixed here**: the re-port put a pre-existing porter defect in
  the diff — `$ARGUMENTS` → `the user's argument` lands inside a single-quoted
  Python literal in the OpenClaw copy, making the Step 1 snippet a
  SyntaxError. Filed as
  `openclaw-porter-arguments-substitution-breaks-single-quoted-python-literals`
  (gate `decision`: three credible fix paths). It lives in
  `scripts/port_skills_to_openclaw.py`, not in this skill body, so it was left
  out of this closure deliberately.

## Closure verification (2026-07-26T12:57:09Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-07-26 — Closure' present

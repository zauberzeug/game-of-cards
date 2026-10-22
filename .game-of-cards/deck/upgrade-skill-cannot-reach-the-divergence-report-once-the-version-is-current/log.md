## 2026-10-04T07:18:10Z — Closure

- **What changed**: `goc/install.py:2132-2140` — `upgrade()`'s "already at
  goc X — nothing to do." short-circuit now prints the divergence report
  after its verdict line (`_emit_divergence_report` over
  `_user_owned_classifications`). Before the fix, the only emitter was
  `_sync_game_of_cards_config(..., emit_report=True)` below that return,
  and a diverged evolving file is `preserved`, a no-op to the plan that
  gates it. `goc/templates/skills/upgrade/SKILL.md` step 1 now says plain
  `goc upgrade` is the whole invocation and the report follows the no-op
  line too. Its "next time someone runs this skill" promise and its
  "does NOT re-run" note were reworded to match. `AGENTS.md`'s upgrade
  contract paragraph records the every-run rule. Mirrors were re-synced
  and the OpenClaw skill was re-ported.
- **Verification**: `reproduce.py` exits 0 (was 1). Its second
  `goc upgrade` at the current version printed `printed report: False`
  before the fix. Now it prints the report with README.md as
  `preserved` / `evolving` and writes nothing. The 3 new regression tests
  failed 3/3 before the fix and pass after it.
- **Audit**: no rubric configured; mechanical fix. (The hook
  `.game-of-cards/hooks/finish-card.md` is the comment stub.) The fix
  restores a documented contract and adds no new default: AGENTS.md says
  `Skill(upgrade)` runs the engine and then reads its divergence report,
  and the skill's own step 1 says the same.
- **Design choice**: I took the card's recommended direction (print on
  the no-op path) over the alternative of a skill-side flag such as
  `--claude` or a new `--report-only`. The report is read-only, so the
  no-op contract the predecessor cards pinned still holds: no writes, and
  the exact verdict line first. The one changed assertion is the pristine
  no-op test, which pinned the verdict line as the *entire* stdout. It
  now pins the verdict, then the report, and nothing else. The no-op
  `--dry-run` shares the short-circuit, so preview and real run stay
  byte-identical. An effecting `--dry-run` is unchanged and still prints
  only its plan.
- **Project impact**: a consumer whose version is already current (the
  usual state after a terminal `goc upgrade`) can now run
  `Skill(upgrade)` and get the reconcile of upstream `README.md` /
  `config.yaml` changes, instead of a silent no-op until the next
  release.
- **Tests**: 1230 passed / 0 failed / 0 xfailed (was 1227; +3 new).
- **Bundled with**: n/a. The related decision-gated
  `upgrade-divergence-report-marks-pristine-config-as-authored-divergence`
  got a log note: its needless `config.yaml` reconcile now reaches every
  skill run, not only runs with engine work.

## Closure verification (2026-10-04T07:18:22Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-04 — Closure' present

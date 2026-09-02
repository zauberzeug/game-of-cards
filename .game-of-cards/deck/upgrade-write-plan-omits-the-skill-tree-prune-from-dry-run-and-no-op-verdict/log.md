## 2026-09-02T05:07:15Z — Closure

- **What changed**: `goc/install.py` — `_sync_skill_tree` grew a `probe=True`
  mode returning the destination files its wipe-and-recopy deletes and does not
  restore; `_plan_upgrade_writes` appends `_plan_skill_prunes`, which calls that
  probe with the arguments `upgrade()` will use and turns each path into
  `PlannedWrite(agent, "delete", path, "harness", kind="skill-prune")`. The
  plan and the deletion now come from one call, so the label cannot drift.
  `_print_plan` and `plan_has_effect` were not touched — the plan-derived design
  picked the repair up for free.
- **Verification**: `reproduce.py` exits 0 (was 1, 2 of 2 assertions failing).
  Same-version bare `goc upgrade` now removes the planted stale file instead of
  printing `already at goc … — nothing to do.`; the older-sentinel dry-run
  prints `claude delete .claude/skills/deck/reference-v1.md` and reports
  `50 writes planned (2 effecting)` where it previously reported
  `49 writes planned (1 effecting)` and named the deletion on zero lines.
  New `tests/test_upgrade_plan_skill_tree_prune.py`: 10 tests, of which 4 fail
  against the pre-fix engine (verified by temporarily removing the
  `_plan_skill_prunes` call) and 6 are inverse-defect guards that hold either
  way — a user-owned skill dir is never planned for deletion, plugin mode plans
  no prune, and `probe=True` writes nothing.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1073 passed / 0 failed / 0 xfailed
- **Also updated**: `AGENTS.md`'s "already at goc X — nothing to do is derived"
  paragraph now states the plan is not writes only and names `_plan_skill_prunes`
  as the shape to copy for the next deletion; the root card
  `dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting` gained
  this card as instance 6 — and instance 5
  (`dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed`,
  closed 2026-07-07), which had been wired as an `advanced_by` edge but never
  written into the `## The instances so far` list.

## Closure verification (2026-09-02T05:07:39Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-09-02 — Closure' present

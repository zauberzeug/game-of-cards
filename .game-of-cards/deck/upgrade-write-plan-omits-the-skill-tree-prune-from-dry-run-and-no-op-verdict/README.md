---
title: upgrade-write-plan-omits-the-skill-tree-prune-from-dry-run-and-no-op-verdict
summary: "`_plan_upgrade_writes` enumerates `PlannedWrite`s only, so the `_sync_skill_tree(replace_skills=True)` prune — which `shutil.rmtree`s each GoC-owned skill dir before recopying — is invisible to the plan. Two consequences from one omission: `goc upgrade --dry-run` never lists a deletion it then performs, and `upgrade()`'s plan-derived `plan_has_effect` verdict reports 'already at goc X — nothing to do' at the same version while the identical stale file IS removed at any other version."
status: open
stage: null
contribution: medium
created: "2026-09-02T04:52:02Z"
closed_at: null
human_gate: none
advances:
  - dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting
advanced_by: []
tags: [bug, infra, api-contract]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# upgrade-write-plan-omits-the-skill-tree-prune-from-dry-run-and-no-op-verdict

(write the design doc here)

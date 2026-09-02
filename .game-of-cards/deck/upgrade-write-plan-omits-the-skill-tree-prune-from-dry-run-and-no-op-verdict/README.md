---
title: upgrade-write-plan-omits-the-skill-tree-prune-from-dry-run-and-no-op-verdict
summary: "`_plan_upgrade_writes` enumerates `PlannedWrite`s only, so the `_sync_skill_tree(replace_skills=True)` prune — which `shutil.rmtree`s each GoC-owned skill dir before recopying — is invisible to the plan. Two consequences from one omission: `goc upgrade --dry-run` never lists a deletion it then performs, and `upgrade()`'s plan-derived `plan_has_effect` verdict reports 'already at goc X — nothing to do' at the same version while the identical stale file IS removed at any other version."
status: active
stage: null
contribution: medium
created: "2026-09-02T04:52:02Z"
closed_at: null
human_gate: none
advances:
  - dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: regression test asserts `_plan_upgrade_writes` emits an effecting entry for a file present inside an eligible (current-template) skill directory that the templates no longer ship, and emits none when the destination tree matches the templates exactly.
  - [ ] TDD: regression test asserts bare `goc upgrade` at the *same* version removes such a stale file instead of printing "already at goc X — nothing to do".
  - [ ] TDD: regression test asserts `goc upgrade --dry-run` names the deletion, and that its "N effecting" count includes it.
  - [ ] MECHANICAL: the prune is modelled as a planned entry (a new `PlannedWrite` kind whose action comes from the pruning executor), NOT as a new `pending_*` term beside `plan_has_effect` — `AGENTS.md` forbids that register by name.
  - [ ] TDD: `reproduce.py` exits zero (both `BUG:` assertions pass).
  - [ ] PROCESS: root card `dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting` gains this instance in its `## The instances so far` list.
worker: {who: "claude[bot]", where: main}
---

# upgrade-write-plan-omits-the-skill-tree-prune-from-dry-run-and-no-op-verdict

`goc upgrade` deletes stale files inside GoC-owned skill directories, but that
deletion is not part of the write plan — so the dry-run never shows it and the
same-version no-op verdict never counts it.

## Location

- `goc/install.py:1427` — `_sync_skill_tree`'s `shutil.rmtree(target)`.
- `goc/install.py:1066` — `_plan_upgrade_writes`, which enumerates only writes.
- `goc/install.py:1981` — `plan_has_effect`, derived from that plan.
- `goc/install.py:1998` — the `already at goc … — nothing to do.` return.

## What's broken

`_sync_skill_tree` owns each *eligible* skill directory wholesale. Its
docstring states the contract:

> `replace_skills=True` wipes only the eligible (current-GoC-template) skill
> directories before recopying them, so a refresh picks up template edits.
> Non-eligible directories are left untouched — `.claude/skills/` may hold
> user-owned skills (or skills from other tools) that GoC does not own and
> must never delete as a side effect of upgrade.

So a file sitting inside `.claude/skills/deck/` that the current templates no
longer ship is GoC-owned garbage, and the executor removes it:

```python
    if replace_skills:
        for name in sorted(eligible):
            target = skills_dst / name
            if target.exists():
                shutil.rmtree(target)
```

That removal is real work. It is not a `PlannedWrite`. `_plan_upgrade_writes`
walks `_plan_writes`, which enumerates one entry per *template file* — there is
no entry shaped like "a destination file the templates do not ship". Its
docstring nevertheless promises the plan is the whole answer:

> `upgrade()` reads its "nothing to do" verdict off this same plan, which is
> what keeps the preview and the real run in agreement and what makes a repair
> added to `upgrade()` covered the moment it is planned, rather than when
> someone remembers to register a signal for it.

One omission, two consequences:

1. **The dry-run under-reports.** `_print_plan` counts effecting writes
   (`goc/install.py:1134`) and prints `N writes planned (M effecting)`. The
   prune is in neither number and appears on no line, so the preview promises
   one effecting write and the real run also deletes a file it never named.

2. **The same-version verdict misses a repair it can perform.**
   `plan_has_effect` is `any(write.action not in _NO_OP_ACTIONS …)` over that
   plan. With no prune entry, it is `False` on an otherwise-current repo, and
   `upgrade()` returns at `goc/install.py:1998`. The identical stale file *is*
   removed whenever `.goc-version` differs — so the same damage gets opposite
   treatment based on nothing but the sentinel value.

Consequence 2 is a surviving hole in the closed predecessor
[goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version](../goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version/),
which replaced a hand-maintained `pending_*` allowlist with this plan-derived
verdict precisely so no repair could be skipped again. Its own comment at
`goc/install.py:1974-1980` states the guarantee — "a repair added below cannot
rejoin the skipped set by forgetting to register a signal here — it is covered
the moment it is planned". The guarantee holds for writes and only for writes:
a repair that *deletes* is never planned, so it was never covered.

## Empirical evidence

`uv run python .game-of-cards/deck/upgrade-write-plan-omits-the-skill-tree-prune-from-dry-run-and-no-op-verdict/reproduce.py`:

```
engine version: 0.0.27.post1.dev362

[part 1] same-version upgrade
  planted .claude/skills/deck/reference-v1.md inside a GoC-owned skill dir
  goc upgrade -> exit 0: already at goc 0.0.27.post1.dev362 — nothing to do.
  stale file still present: True

[part 2] same damage, sentinel rewound to 0.0.1
  goc upgrade --dry-run -> exit 0
    goc upgrade (dry-run) — agents: claude — 49 writes planned (1 effecting)
  plan lines naming the deletion: 0
  real goc upgrade -> exit 0; stale file deleted: True

DEFECT PRESENT (2 of 2 assertions failed):
  BUG: same-version `goc upgrade` reported 'nothing to do' and left the stale skill file in place
  BUG: `goc upgrade --dry-run` listed no deletion, then the real run removed the file
```

## Why it matters

**Reachability.** The offending state — a destination file inside an eligible
skill dir with no template counterpart — is produced by ordinary upstream
churn: any release that *removes* a file from a shipped skill (a retired
`reference.md`, a renamed sibling asset) leaves exactly this shape in every
vendored consumer. `_iter_skill_assets` walks the template tree, so the
orphan is invisible to the plan by construction, not by oversight in one
branch. Two live paths reach the un-repaired variant: a consumer already at
the current version (the sentinel matches, so the prune never runs), and any
`goc upgrade --dry-run` reader at any version.

The stale file is not inert — it sits inside a skill directory an agent
loads, so retired guidance keeps being read as current. And the two
consequences pull against each other in review: the dry-run says the upgrade
is a one-write no-op, so the deletion looks like data loss when it happens
and looks like a broken upgrade when it does not.

This is the sixth instance of
[dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting](../dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting/)
and the first where the un-mirrored executor decision is a *deletion* inside
the `install.py` write plan rather than a guard on a write.
[migrate-dry-run-omits-legacy-tree-removal-for-identical-only-trees](../migrate-dry-run-omits-legacy-tree-removal-for-identical-only-trees/)
is the closest sibling — the same "dry-run hides a deletion" shape, in
`migrate` rather than `upgrade`. Distinct from
[goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install](../goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install/),
which is the inverse: there the executor *declines* to delete a whole
non-eligible directory; here it deletes inside an eligible one and the plan
does not say so.

## Fix

Model the prune as a planned entry so both readers of the plan pick it up for
free. In `_plan_writes`, after the per-agent skill-asset writes, walk the
*destination* eligible skill dirs and emit one entry per file with no template
counterpart — a new `kind` (e.g. `"skill-prune"`) carrying the destination
path. Give `_upgrade_write_action` (`goc/install.py:1035-1063`) a branch that
asks the pruning executor: effecting when the orphan is present, `unchanged`
otherwise. `_print_plan` and `plan_has_effect` then need no change, which is
the point of the plan-derived design.

Explicitly **not** the fix: a new `pending_*` term beside `plan_has_effect`.
`AGENTS.md` rules that out by name — "Do not reintroduce a `pending_*`
allowlist term for a new write; that per-site register is what let four
repairs go unreachable at the same version."

The root card's architectural decision (derive the plan from a recording
executor pass) would subsume this instance. This card is the concrete hole
worth closing meanwhile; if the root decision lands first, close this one as
superseded by it.

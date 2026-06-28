---
title: openclaw-skill-porter-leaves-empty-orphan-subdir-when-nested-sibling-removed
status: done
stage: null
contribution: medium
created: "2026-06-19T05:33:01Z"
closed_at: "2026-06-19T05:38:51Z"
human_gate: none
advances:
  - sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting
advanced_by: []
tags: [bug, infra]
summary: "scripts/port_skills_to_openclaw.py prunes orphaned sibling FILES but never rmdir's a now-empty nested subdir left behind when a source sibling under a subdirectory is removed. drifted_skills() skips directories, so `--check` and tests/test_plugin_mirror_parity.py stay green while the empty orphan dir ships in the OpenClaw payload. This is the porter's nested-subdir equivalent of the already-closed sync-side fix (sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes); the porter was never given the same empty-dir prune."
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — after a nested source sibling subdir is removed and the porter re-runs, the corresponding `openclaw-plugin/skills/<skill>/<subdir>/` is gone (no empty orphan), and `drifted_skills()` FLAGS the orphan while one remains.
  - [x] TDD: removing only one file from a still-populated subdir leaves that subdir intact (no over-eager rmdir of a dir that still mirrors a live source sibling).
  - [x] MECHANICAL: `python scripts/port_skills_to_openclaw.py --check` green and `uv run python -m unittest discover -s tests` pass on a clean tree after the fix.
---

# OpenClaw skill porter leaves an empty orphan subdir when a nested sibling is removed

## Location

`scripts/port_skills_to_openclaw.py` — the write-path sibling prune
(lines 317-327) and the `drifted_skills()` drift guard (lines 250-268).

## What's broken

`_iter_skill_siblings` walks each source skill dir with `rglob("*")`
(`scripts/port_skills_to_openclaw.py:165`), so a nested asset like
`goc/templates/skills/card-schema/extra/asset.txt` is ported with its
subdirectory intact (`port_sibling` does `dst.parent.mkdir(parents=True)`).

When the source `extra/` subdir is later renamed or removed, the
write-path prune removes the orphaned **file** but never the now-empty
**directory**:

```python
        # Prune dst-only siblings (sibling renamed or removed in source) so
        # the OpenClaw payload tracks the source-of-truth exactly.
        if dst_skill_dir.is_dir():
            for asset in sorted(dst_skill_dir.rglob("*")):
                if asset.is_dir() or asset.name == "SKILL.md":
                    continue
                ...
                if asset.relative_to(dst_skill_dir) not in src_siblings:
                    asset.unlink()
                    siblings_pruned += 1
```

`if asset.is_dir(): continue` skips directories, and there is no
`rmdir` anywhere in the file (`grep rmdir` → none). The `drifted_skills()`
guard has the identical blind spot — it iterates `dst_skill_dir.rglob("*")`
and `continue`s on `asset.is_dir()` (lines 252-253), so an empty dst-only
subdir contributes nothing to the drift list and `--check` exits 0.

## Why it matters

This is the porter's instance of a defect already fixed on the sync
side: [sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes](../sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes/)
closed by adding a bottom-up empty-dir prune to `_sync_dir`
(`scripts/sync_plugin_assets.py:310-327`) and teaching `_check_changes`
to flag empty dst-only orphan dirs (`scripts/sync_plugin_assets.py:510-517`).
The OpenClaw porter — a separate sync mechanism — never received the same
treatment. The closest porter card,
[openclaw-skill-porter-never-prunes-orphaned-ported-skills](../openclaw-skill-porter-never-prunes-orphaned-ported-skills/),
covers only whole orphaned *top-level* skill dirs (handled by
`shutil.rmtree`), not empty *nested* subdirs.

**Reachability path:** `_iter_skill_siblings` is a full recursive walk,
mirroring the full-tree copy the other sync mechanisms (`goc install`,
the Claude/Codex mirror sync) already perform — so any portable skill
may grow nested asset subdirs (`card-schema` already ships the sibling
`schema.yaml` flat; a future grouped asset dir is the natural extension).
When such a subdir is removed in `goc/templates/skills/...` and a
maintainer re-runs the porter, the empty subdir is orphaned in
`openclaw-plugin/skills/`. Git does not track empty dirs, so the
auto-staged review looks clean and the CI parity test
(`tests/test_plugin_mirror_parity.py`, which reuses `drifted_skills()`)
stays green — yet the empty orphan dir is materialized into any
wheel/tarball/npm copy of the payload shipped to OpenClaw consumers.

## Empirical evidence

See `reproduce.py` (sandboxes a copy of the real skill trees so it never
mutates the repo). On the **pre-fix** tree the two diagnostic lines read
`empty 'extra/' orphan dir lingers after re-port: True` and
`drift guard flags a bare empty orphan dir: False` → `FAIL` (exit 1).
After the fix all six checks pass (exit 0):

```
drifted_skills flags the orphan before re-port : True
empty 'extra/' orphan dir lingers after re-port: False
populated 'kept/' subdir left intact           : True
removed 'kept/b.txt' pruned                    : True
drift guard quiet after clean re-port          : True
drift guard flags a bare empty orphan dir      : True
PASS: porter prunes empty orphan subdir and the guard catches it
```

## Fix

Mirror the already-shipped sync-side pattern in `port_skills_to_openclaw.py`:

1. After the write-path file prune (line 327), add a bottom-up empty-dir
   prune over `dst_skill_dir.rglob("*")` in reverse-sorted order, skipping
   `SKILL.md`'s own dir and guarding with a "source subdir still exists"
   check — `rmdir` is self-guarding (fails on non-empty), matching
   `_sync_dir` (`sync_plugin_assets.py:310-327`).
2. In `drifted_skills()`, flag an empty dst-only subdir whose source
   counterpart no longer exists, mirroring `_check_changes`
   (`sync_plugin_assets.py:510-517`), so detection and remediation stay
   symmetric across all three sync mechanisms.

---
title: sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes
summary: "When a source skill directory under goc/templates/skills/ is renamed or removed, scripts/sync_plugin_assets.py prunes the orphaned FILES from the claude-plugin/ and codex-plugin/ mirrors but never rmdir's the now-empty skill directory. The `--check` mode walks rglob and skips directories, so it reports OK while a stale empty dir remains and ships in any wheel/tarball copy of the payload (git masks empty dirs, so the auto-stage commits cleanly). The OpenClaw porter does this correctly (shutil.rmtree). Parked unverified pending a reproduce.py."
status: done
stage: null
contribution: medium
created: "2026-05-27T04:04:34Z"
closed_at: 2026-05-27T05:42:43Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — after a source skill dir is removed and sync runs, the corresponding claude-plugin/ and codex-plugin/ skill dirs are gone (no empty orphan), and `--check` FAILs while one remains.
  - [x] TDD: removing only some files from a skill dir still syncs correctly (no over-eager rmdir of a dir that still has synced content).
  - [x] PROCESS: confirm-or-disprove recorded in log.md; drop the `unverified` tag once reproduce.py lands.
worker: {who: "claude[bot]", where: main}
---

# `sync_plugin_assets.py` leaves orphaned empty skill dirs, and `--check` passes anyway

## Hypothesis (file:line, verbatim)

`scripts/sync_plugin_assets.py` `_sync_dir` (≈lines 248-262) and
`_sync_codex_skill_tree` (≈lines 339-348) prune orphaned **files**
(`item.unlink()`) from the plugin mirrors but never `rmdir` a skill directory
that has become empty because its source was renamed/removed. The
empty-directory prune that does exist runs only for paths in the `excludes`
set, not for ordinary orphans.

The `--check` walks (≈lines 437-449 and 392-401) iterate `dst.rglob("*")` and
`continue` on `item.is_dir()`, so an empty directory contributes nothing to the
drift comparison — `--check` prints `OK` even though a stale empty dir remains.

Contrast: the OpenClaw porter prunes orphans with `shutil.rmtree(orphan)`
(`scripts/port_skills_to_openclaw.py` ≈line 248), so it does NOT leave empty
dirs — evidence of the intended behavior and that the two pruners diverge.

## Why this rots silently

Git does not track empty directories, so the auto-sync's `git add` of the
deleted files commits "cleanly" while the empty directory persists on disk.
A wheel/sdist built from that working tree copies the empty dir into the
payload. CI's `--check` never catches it because it skips directories.

## Why deferred (unverified)

Reported by the install/sync hunter but not yet reproduced end-to-end in this
session (verifying it requires creating then deleting a template skill dir and
running the real sync, which mutates the working tree). Direct sibling of the
just-closed
[openclaw-skill-porter-never-prunes-orphaned-ported-skills](../openclaw-skill-porter-never-prunes-orphaned-ported-skills/)
(commit 016485e) — that card fixed orphan pruning for the porter; this is the
same gap for the claude/codex dir-sync, plus the additional `--check`
blind-spot for empty dirs.

## Falsification recipe

1. `mkdir goc/templates/skills/zzz-temp-skill && echo '---\nname: zzz\n---\n' > goc/templates/skills/zzz-temp-skill/SKILL.md`
2. `python scripts/sync_plugin_assets.py` (creates the mirror dirs)
3. `rm -rf goc/templates/skills/zzz-temp-skill`
4. `python scripts/sync_plugin_assets.py` again, then
   `python scripts/sync_plugin_assets.py --check`

DEFECT if `claude-plugin/skills/zzz-temp-skill/` and
`codex-plugin/skills/zzz-temp-skill/` remain as empty dirs AND `--check` prints
`OK`. DISPROVED if the dirs are removed or `--check` FAILs. Clean up the temp
dirs afterward regardless of outcome.

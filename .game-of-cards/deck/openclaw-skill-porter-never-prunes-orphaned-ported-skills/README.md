---
title: openclaw-skill-porter-never-prunes-orphaned-ported-skills
summary: "`port_skills_to_openclaw.py` only iterates source skill dirs — it never walks `openclaw-plugin/skills/` for ported skills that no longer have a source. When a source skill is renamed or removed, the stale ported copy lingers forever and `--check` (plus the CI parity test that reuses `drifted_skills()`) stays green, shipping a defunct skill in the OpenClaw payload."
status: done
stage: null
contribution: medium
created: "2026-05-27T03:47:07Z"
closed_at: 2026-05-27T03:55:18Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — after creating an orphan `openclaw-plugin/skills/<bogus>/SKILL.md` (no matching source dir), `drifted_skills()` flags it AND a full re-port removes it.
  - [x] TDD: `drifted_skills()` reports dst-only ported skill dirs (orphans) as drift, matching the dst-only handling in `scripts/sync_plugin_assets.py::_check_changes`.
  - [x] TDD: the porter's re-port pass (`main` without `--check`) prunes orphaned ported skill dirs under `DST_DIR`, leaving only skills that correspond to a current portable source skill.
  - [x] MECHANICAL: `uv run goc validate` clean; `python scripts/port_skills_to_openclaw.py --check` green; `python scripts/sync_plugin_assets.py --check` green; existing parity test `tests/test_plugin_mirror_parity.py` still passes.
worker: {who: "claude[bot]", where: main}
---

# OpenClaw skill porter never prunes orphaned ported skills

`scripts/port_skills_to_openclaw.py` ports each skill under
`goc/templates/skills/` into `openclaw-plugin/skills/`. Both the drift
guard and the re-port pass are **strictly source-driven** — they iterate
source dirs and never walk the destination tree for ported skills that
have lost their source. A renamed or deleted source skill therefore
leaves a stale `openclaw-plugin/skills/<old>/SKILL.md` that lingers
indefinitely, and the `--check` guard (plus the CI parity test that
reuses it) stays green while a defunct skill ships in the OpenClaw
payload.

## Location

- `scripts/port_skills_to_openclaw.py:166-172` — `drifted_skills()`
  loops `_portable_skill_dirs()` (source) only.
- `scripts/port_skills_to_openclaw.py:202-204` — `main()` re-port loops
  source dirs only; no deletion pass.

## What's broken

```python
def drifted_skills() -> list[Path]:
    drifted: list[Path] = []
    for skill_dir in _portable_skill_dirs():          # line 166 — source-driven
        dst = DST_DIR / skill_dir.name / "SKILL.md"
        expected = render_skill(skill_dir / "SKILL.md")
        actual = dst.read_text(encoding="utf-8") if dst.is_file() else None
        if actual != expected:
            drifted.append(dst)
    return drifted
```

```python
    DST_DIR.mkdir(parents=True, exist_ok=True)
    ported = 0
    for skill_dir in _portable_skill_dirs():          # line 202 — source-driven
        port_skill(skill_dir / "SKILL.md", DST_DIR / skill_dir.name / "SKILL.md")
        ported += 1
```

Neither pass enumerates `DST_DIR`. A ported skill dir with no source
counterpart is invisible to both.

**The asymmetry.** `scripts/sync_plugin_assets.py` — which mirrors the
Claude/Codex/OpenClaw *engine* trees — DOES handle dst-only files: its
`_sync_dir` deletes dst paths absent from src, and `_check_changes`
flags them (guarded by `preserve_files`). The skill porter, by contrast,
silently keeps orphans. CLAUDE.md documents that skill renames are a
recurring event in this repo (e.g. `extend-deck → audit-deck`,
`improve-deck → refine-deck`, `bootstrap → kickoff`), so this is not a
hypothetical edge.

The CI drift guard `tests/test_plugin_mirror_parity.py` calls
`drifted_skills()`, so the same blind spot is what gates the build —
meaning a rename that orphans a ported skill turns the build *green*,
not red.

## Empirical evidence

See `reproduce.py`. With a synthetic orphan
`openclaw-plugin/skills/<bogus>/SKILL.md` (no matching source), the
porter is now orphan-aware:

```
drifted_skills() flags orphan? True
orphan still present after re-port? False
```

`drifted_skills()` returns the orphan and a full re-port deletes it
(`reproduce.py` exits 0).

> The reproducer creates and removes its own synthetic orphan dir; it
> does not mutate any committed ported skill.

## Why it matters

The whole point of the `--check` guard and the CI parity test is to keep
the OpenClaw payload honest without auto-staging the port (the porter
applies non-trivial normalization that is reviewed by hand). An
orphan-blind guard defeats that contract precisely at the moment it
matters most — a skill rename — letting a stale, removed-upstream skill
ship to OpenClaw consumers undetected.

## Fix (applied)

Both the guard and the re-port pass are now destination-aware, mirroring
`sync_plugin_assets.py`'s dst-only handling:

- `_expected_dst_names()` computes the set of skill names that belong in
  `DST_DIR` (one per portable source dir) — the single source of truth
  reused by both the drift check and the prune so they cannot diverge.
- `_orphaned_ported_dirs(expected)` walks `DST_DIR` and returns ported
  skill dirs whose name is not in `expected`, skipping host-specific
  complement dirs (`claude-`/`codex-` prefixed) which this porter never
  manages.
- `drifted_skills()` appends each orphan's `SKILL.md` to its result, so
  `--check` and the CI parity test go red on an orphan.
- `main()`'s re-port branch `shutil.rmtree`s each orphan after porting.

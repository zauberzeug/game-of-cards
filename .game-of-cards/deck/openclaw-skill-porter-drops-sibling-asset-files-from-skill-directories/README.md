---
title: openclaw-skill-porter-drops-sibling-asset-files-from-skill-directories
summary: "scripts/port_skills_to_openclaw.py only walks `SKILL.md` and ignores every sibling file in a skill directory. card-schema/schema.yaml ships to claude-plugin, codex-plugin, .claude/skills/, and .codex/skills/ but is silently absent from openclaw-plugin/skills/card-schema/. The drift guard reads the same SKILL.md-only path, so CI does not flag the desync."
status: done
stage: null
contribution: high
created: "2026-05-29T21:37:45Z"
closed_at: "2026-05-30T16:29:37Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (porter copies every sibling asset; openclaw-plugin/skills/card-schema/schema.yaml exists and matches goc/templates/skills/card-schema/schema.yaml byte-for-byte)
  - [x] TDD: drifted_skills() detects sibling-asset drift — hand-mutate openclaw-plugin/skills/card-schema/schema.yaml, then `python scripts/port_skills_to_openclaw.py --check` exits 1 and names the drifted path
  - [x] MECHANICAL: openclaw-plugin/skills/card-schema/schema.yaml committed (was never present)
  - [x] PROCESS: AGENTS.md's "OpenClaw plugin payload" section names the sibling-asset coverage so a future reader cannot conclude the porter is SKILL.md-only by design
worker: {who: "claude[bot]", where: main}
---

# openclaw-skill-porter-drops-sibling-asset-files-from-skill-directories

## Location

- `scripts/port_skills_to_openclaw.py:140-142` — `port_skill` writes a single `SKILL.md` dst path.
- `scripts/port_skills_to_openclaw.py:200-208` — `drifted_skills` only compares `dst = DST_DIR / skill_dir.name / "SKILL.md"`.
- `scripts/port_skills_to_openclaw.py:240-242` — `main` calls `port_skill(skill_dir / "SKILL.md", ...)`. No sibling walk.
- Symptom site: `openclaw-plugin/skills/card-schema/` contains only `SKILL.md`; every other target (`goc/templates/skills/card-schema/`, `claude-plugin/skills/card-schema/`, `codex-plugin/skills/card-schema/`, `.claude/skills/card-schema/`, `.codex/skills/card-schema/`) also contains `schema.yaml`.

## What's broken

The porter is structured around a single source file per skill — `SKILL.md` is the only path it ever reads or writes. From `scripts/port_skills_to_openclaw.py`:

```python
def port_skill(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(render_skill(src), encoding="utf-8")
```

```python
def drifted_skills() -> list[Path]:
    ...
    for skill_dir in _portable_skill_dirs():
        dst = DST_DIR / skill_dir.name / "SKILL.md"
        rendered = render_skill(skill_dir / "SKILL.md")
        actual = dst.read_text(encoding="utf-8") if dst.is_file() else None
        if actual != rendered:
            drifted.append(dst)
```

Every other consumer of `goc/templates/skills/` walks the full tree with `rglob("*")`:

- `goc/install.py:874` — `for asset in skill_dir.rglob("*"):` (install path).
- `scripts/sync_plugin_assets.py:264` — `for src_item in sorted(src.rglob("*")):` (claude-plugin sync).
- `scripts/sync_plugin_assets.py:369-384` — `_sync_codex_skill_tree` walks `src.rglob("*")`.
- `scripts/sync_plugin_assets.py:411` — same for `.claude/skills/` and `.codex/skills/` mirrors.

The OpenClaw porter is the only outlier. The `drifted_skills()` guard reads the same single-file shape, so CI never sees the divergence — `tests/test_plugin_mirror_parity.py` calls `drifted_skills()` and that function never asks the filesystem about `schema.yaml`.

Currently `card-schema/schema.yaml` is the only sibling asset in the source tree, but the structural defect applies to any future skill that grows a non-SKILL.md companion file (a `decision-form.html` for a decision-gate skill, an `examples.json`, an `.svg` diagram). Each one would silently fail to reach OpenClaw consumers.

The `AGENTS.md` "OpenClaw plugin payload" section advertises the byte-for-byte engine pair as the parity guarantee:

> The auto-synced engine pair (`goc -> openclaw-plugin/goc`) is enforced by the same byte-for-byte tripwire as the Claude one. Skills are NOT auto-synced into the commit — they go through the porting script, whose output is reviewed and committed by hand …

That paragraph is silent on what "porting script" means for sibling assets. A reader infers the porter copies whatever's in the skill dir; the actual implementation is SKILL.md-only.

## Empirical evidence

After running `reproduce.py`:

```
openclaw-plugin missing 1 file(s) present in goc/templates: card-schema/schema.yaml
drifted_skills() reports: []   # CI guard sees nothing wrong
```

(See `reproduce.py` for the full check.)

## Why it matters

Reachability path: a maintainer adds a sibling asset to any `goc/templates/skills/<name>/` directory (today the only instance is `card-schema/schema.yaml`; tomorrow it could be any decision-gate skill shipping an HTML form per the `card-skills-document-html-as-sibling-artifact-pattern` convention). The sync hook regenerates `claude-plugin/`, `codex-plugin/`, `.claude/skills/`, and `.codex/skills/` correctly. `goc install` copies the sibling into consumer repos correctly. But `python scripts/port_skills_to_openclaw.py` ignores the sibling, so `openclaw-plugin/skills/<name>/` ships with only `SKILL.md`. OpenClaw users — and the OpenClaw plugin manifest's claim of skill-parity with the other hosts — silently miss whatever the sibling carries.

For `card-schema/schema.yaml` specifically: the file is the machine-readable schema reference (parsed by `goc validate`, mirrored to consumer repos via `goc install`). An OpenClaw plugin install that wants to read the schema as data instead of parsing the SKILL.md prose has nothing to read.

The drift guard is the second-order failure. `drifted_skills()` was added to catch SKILL.md skew ([openclaw-plugin-ported-skills-drift-silently-from-templates](../openclaw-plugin-ported-skills-drift-silently-from-templates/), closed) and later extended to catch dst-only orphan skill *directories* ([openclaw-skill-porter-never-prunes-orphaned-ported-skills](../openclaw-skill-porter-never-prunes-orphaned-ported-skills/), closed). Neither extension covers src-only sibling *files* inside a present dst dir — exactly the shape that breaks today. That makes the parity claim narrower than the parity guarantee implies.

## Decision

*Resolved 2026-05-30T13:56:58Z:* Option A: extend the porter to walk skill_dir.rglob('*') — port SKILL.md via render_skill and copy every other file verbatim (excluding __pycache__/*.pyc, mirroring _iter_skill_assets); extend drifted_skills() and the orphan check symmetrically for siblings

*Reasoning:* aligns the OpenClaw porter with the four other plugin consumers that already walk full trees, honors the cross-host parity promise, and gives future sibling assets coverage for free instead of re-litigating this card each time a skill grows a companion file

## Fix

In `scripts/port_skills_to_openclaw.py`, replace the SKILL.md-only walk in three places:

1. `port_skill` (line 140) — split into `port_skill_md` (current behavior on `SKILL.md`) plus `port_sibling` (verbatim copy of one path). The `main` loop iterates `skill_dir.rglob("*")` and dispatches.
2. `drifted_skills` (line 191) — for each portable skill dir, walk both `skill_dir.rglob("*")` and `(DST_DIR / skill_dir.name).rglob("*")`; emit drift entries for missing siblings, extra dst-only siblings, and content mismatches.
3. `_orphaned_ported_dirs` — unchanged at the dir level; the new sibling walk in `drifted_skills` covers file-level orphans.

After implementing, run `python scripts/port_skills_to_openclaw.py` to write `openclaw-plugin/skills/card-schema/schema.yaml`, then `--check` to confirm zero drift.

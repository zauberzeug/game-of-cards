---
title: openclaw-porter-orphan-check-misses-asset-only-skill-dirs
summary: "The OpenClaw porter's orphan detection is SKILL.md-gated: a dst-only dir under openclaw-plugin/skills/ that holds only sibling assets (no SKILL.md) is invisible to `--check`, never pruned by a re-port, and ships in the published payload — while AGENTS.md claims the check covers sibling assets and orphaned dirs \"symmetrically\". Decision needed: extend the orphan predicate, flag-without-prune, or fold into the open orphan-pruning meta-fix."
status: open
stage: null
contribution: medium
created: "2026-07-17T01:07:16Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, documentation, meta-fix]
definition_of_done: |
  - [ ] PROCESS: decision recorded (extend predicate vs flag-only vs fold into the orphan-pruning meta-fix)
  - [ ] TDD: reproduce.py exits zero (an asset-only dst-only dir is flagged by `--check` / handled per the decision)
  - [ ] MECHANICAL: AGENTS.md "symmetrically" claim reconciled with the implemented behavior
  - [ ] TDD: `uv run python -m unittest discover -s tests` passes (test_plugin_mirror_parity covers the new case)
---

# OpenClaw porter orphan check misses asset-only skill dirs

## Location

`scripts/port_skills_to_openclaw.py:229-236` (`_orphaned_ported_dirs`), used
by both `drifted_skills()` (line 296) and the write-mode prune (line 375).

## What's broken

Orphan detection requires a `SKILL.md` to consider a dst-only dir stale:

```python
    for child in sorted(DST_DIR.iterdir()):
        if not child.is_dir() or child.name in expected:
            continue
        if any(child.name.startswith(prefix) for prefix in HOST_PREFIXES):
            continue
        if (child / "SKILL.md").is_file():
            orphans.append(child)
```

A dst-only dir under `openclaw-plugin/skills/` holding only sibling assets
(e.g. a leftover `schema.yaml` after an interrupted prune or a
partially-removed skill) is neither flagged by `--check` nor pruned by a
re-port. Its files also escape the per-skill extra-sibling check, because
that loop iterates `_portable_skill_dirs()` — source dirs only. The
contradicted doc (AGENTS.md, "OpenClaw plugin payload" section):

> The check covers SKILL.md content, sibling assets (missing, extra, or
> content-mismatched), and orphaned ported skill dirs symmetrically.

## Empirical evidence

`reproduce.py` plants `openclaw-plugin/skills/zombie-repro-dir/asset.txt`
(no SKILL.md), runs `--check`, then a real re-port, and restores the tree:

```
--check exit code with asset-only zombie dir present: 0 (expected nonzero)
zombie survived a full re-port: True
DEFECT CONFIRMED: asset-only dst-only dir is invisible to check and prune
```

Contrast: the same dir WITH a `SKILL.md` is flagged and pruned.

## Why it matters

`tests/test_plugin_mirror_parity.py` gates CI on `drifted_skills()`, so a
stale asset-only dir keeps CI green while shipping in the npm-published
`openclaw-plugin/` payload — permanently, since no mechanism ever removes
it. Reachability: an interrupted prune, a hand-edit, or a future porter bug
that removes `SKILL.md` before siblings. This is a residual hole of the
closed
[openclaw-skill-porter-never-prunes-orphaned-ported-skills](../openclaw-skill-porter-never-prunes-orphaned-ported-skills/)
(which introduced the SKILL.md-gated prune) and an instance of the open
meta-fix
[sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting](../sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting/).

## Decision required

The SKILL.md gate exists as deliberate caution (the docstring: host-prefixed
complement dirs "are never managed by this porter"). Three credible paths:

1. **Extend the predicate** — treat any non-host-prefixed dst-only dir as an
   orphan, SKILL.md or not. Simple and symmetric; risk: deletes a dir a
   human parked under `openclaw-plugin/skills/` for other reasons (nothing
   legitimately lives there today, but the prune is `shutil.rmtree`).
2. **Flag without pruning** — add asset-only dst-only dirs to
   `drifted_skills()` (CI red, human resolves) but keep write-mode prune
   SKILL.md-gated. Safer; leaves `--check`/write-mode asymmetric in the
   other direction.
3. **Fold into the meta-fix** — the open umbrella card wants one shared
   orphan-pruning/drift-detection helper across the sync mechanisms; fixing
   the predicate there fixes this instance without another local variant.
   Cost: this hole stays open until the umbrella lands.

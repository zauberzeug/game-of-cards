---
title: create-card-and-deck-skills-claim-goc-new-scaffolds-a-reproduce-py-stub
summary: "Two shipped skill descriptions advertised a `reproduce.py` stub as a co-equal deliverable of `goc new`, alongside the frontmatter and DoD scaffold the tool genuinely writes — but `goc new` never writes a `reproduce.py` (the skill's own Step 6 correctly frames it as a manual authoring step). The descriptions overstated the tool's behavior; fixed by correcting the skill descriptions."
status: done
stage: null
contribution: medium
created: "2026-06-25T19:13:44Z"
closed_at: "2026-06-25T19:16:05Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: a regression test asserts the create-card/deck skill descriptions do not promise an auto-scaffolded reproduce.py stub, paired with the actual `goc new` file-set contract (README.md + log.md only)
  - [x] MECHANICAL: the create-card and deck skill descriptions are reworded to match the tool's real behavior (reproduce.py is a manual Step-6 authoring step, not a scaffold)
  - [x] MECHANICAL: plugin mirrors + OpenClaw port re-synced; `scripts/sync_plugin_assets.py --check` and `scripts/port_skills_to_openclaw.py --check` are clean
  - [x] `uv run goc validate` passes
  - [x] `uv run python -m unittest discover -s tests` passes
---

# create-card / deck skills claim `goc new` scaffolds a reproduce.py stub it never writes

## Summary

Two shipped skill descriptions advertise a `reproduce.py` stub as a
co-equal deliverable of filing a card, alongside two things the tool
genuinely writes (frontmatter + DoD scaffold). But `goc new` never
writes a `reproduce.py` — the same skill's own body (Step 6) correctly
frames it as a *manual* authoring step. The descriptions overstate the
tool's behavior.

## Location

- `goc/templates/skills/create-card/SKILL.md:3` (frontmatter `description`)
- `goc/templates/skills/deck/SKILL.md:248` (the `Skill(create-card)` catalogue entry)
- Refuted by `goc/engine.py:4905` (`_cmd_new`), which writes only
  `README.md` (`engine.py:4967`) and `log.md` (`engine.py:4968`).

## What's broken

The `create-card` description (`create-card/SKILL.md:3`) reads:

> File a new card with frontmatter, **DoD scaffold, and (for bugs) reproduce.py stub.**

The `deck` catalogue entry (`deck/SKILL.md:248`) reads:

> `Skill(create-card)` — file a new card with proper frontmatter,
> **DoD scaffold, and (for bug-class) reproduce.py stub.**

Both list "reproduce.py stub" as a co-equal deliverable next to two
artifacts the tool *does* auto-write (frontmatter + the DoD scaffold
line), so the natural reading is that all three are scaffolded by
`goc new`.

The code refutes it. `_cmd_new` (`engine.py:4905`) ends with exactly
two file writes:

```python
(card_dir / "README.md").write_text(emit_frontmatter(fm, body=body))   # engine.py:4967
(card_dir / "log.md").write_text("")                                    # engine.py:4968
```

There is no `reproduce.py` write in `_cmd_new` or anywhere on the
`goc new` path. The skill's own body confirms reproduce.py is
hand-authored: `create-card/SKILL.md:258` is titled
**"Step 6 — write `reproduce.py` (bug-class only)"** and instructs the
agent to write it. So the body is self-consistent; only the
description / catalogue lines assert a stub the tool produces.

## Empirical evidence

`reproduce.py` scaffolds a throwaway bug-class card via the engine's
`_cmd_new` into a temp deck and lists the resulting directory:

```
description claims reproduce.py stub : True
goc new --tag bug wrote files        : ['README.md', 'log.md']
reproduce.py present after goc new    : False
DEFECT CONFIRMED: description promises a reproduce.py stub that goc new never writes.
```

## Why it matters

`goc new` is reached by `Skill(create-card)` Step 1 and by the
autonomous audit-deck filing path. An agent (or human) reading the
skill description expects the tool to drop a reproduce.py stub it can
fill in; instead it must hand-write the file per Step 6. The cost is
low (a missing-stub surprise, not a wrong action — the body corrects
the workflow), but a skill description that contradicts the tool it
documents is exactly the doc-drift the audit discipline exists to
catch. The same skill being internally inconsistent (accurate body,
overstated description) is the tell.

This sits in the same doc-drift class as
[next-card-reclassify-checklist-cites-nonexistent-docs-framework-path](../next-card-reclassify-checklist-cites-nonexistent-docs-framework-path/)
(a SKILL body citing a path that does not exist) — different file,
different claim, but the same "shipped guidance asserts something that
isn't true" shape.

## Fix

Reword both description lines so reproduce.py is described as a
manual authoring step rather than an auto-scaffolded artifact, e.g.:

- `create-card/SKILL.md:3`: "File a new card with frontmatter and a
  DoD scaffold (plus a reproduce.py authoring step for bug-class cards)."
- `deck/SKILL.md:248`: "file a new card with proper frontmatter and a
  DoD scaffold (reproduce.py is authored by hand for bug-class cards)."

Edit only the source-of-truth templates under `goc/templates/skills/`,
then re-run `scripts/sync_plugin_assets.py` and
`scripts/port_skills_to_openclaw.py` to refresh the five mirrors. Add a
regression guard in `tests/test_guidance_accuracy.py`.

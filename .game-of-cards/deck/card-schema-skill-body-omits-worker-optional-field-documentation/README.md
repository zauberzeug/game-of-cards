---
title: card-schema-skill-body-omits-worker-optional-field-documentation
status: done
stage: null
contribution: medium
created: "2026-06-25T01:58:12Z"
closed_at: "2026-06-25T02:04:05Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, api-contract]
summary: "The `card-schema` skill advertises itself as the canonical reference for optional fields and documents 10 of the 11 — but `worker` has no field-reference section in the body, even though the sibling bundled `schema.yaml` lists it under `optional_fields` and the engine fully implements it. A reader asking the skill about `worker` semantics finds nothing. The corrective content already exists verbatim in AGENTS.md; this is a doc-only relocation, not a design call."
definition_of_done: |
  - [x] Add a `worker` optional-field subsection to `goc/templates/skills/card-schema/SKILL.md`, in the same style as the other optional-field sections, porting the spec from AGENTS.md "Card authoring rules → `worker` field" (flat-string vs `{who, where}` mapping; flat form is sugar for `{who: <value>}`; unregistered free-form value; persists after close; auto-populated at claim; filter via `goc --worker` / `GOC_WORKER`).
  - [x] `grep -niw worker goc/templates/skills/card-schema/SKILL.md` returns the new field-reference subsection (not just the unrelated prose line).
  - [x] Plugin/skill mirrors regenerated via the sync hook (`.claude/`, `.codex/`, plugin payloads) and the OpenClaw port; `python scripts/sync_plugin_assets.py --check` and `scripts/port_skills_to_openclaw.py --check` pass.
  - [x] `uv run python -m unittest discover -s tests` passes; `uv run goc validate` passes.
  - [x] (Optional) a regression test asserting every `optional_fields` entry in the bundled `schema.yaml` is mentioned in the SKILL.md body, to close the class.
worker: {who: "claude[bot]", where: main}
---

# `card-schema` skill body omits documentation of the `worker` optional field

## Problem

`goc/templates/skills/card-schema/SKILL.md` advertises itself (frontmatter,
line 3) as the canonical reference for "required/optional fields … field
semantics," and gives every optional field a body section: `summary`, `stage`,
`closed_at`/`created`, the `supersedes`/`superseded_by` graph,
`waiting_on`/`waiting_until` (the three-axis model), and `tags` (canonical
tags). The lone exception is **`worker`**.

The bundled sibling `goc/templates/skills/card-schema/schema.yaml:18` lists
`worker` under `optional_fields`, and the engine fully implements it
(`engine.py` validates "string or mapping with 'who'", auto-populates on claim,
and exposes `--worker` / `GOC_WORKER`, `goc status --worker-who/--worker-where`,
`goc new --worker`). But the SKILL.md body never documents it — the only
"worker" occurrence is unrelated prose:

```
637:   it. An autonomous `pull-card` / `/loop` worker halts on the whole
```

So the skill's own bundled schema declares a field that the skill's body — the
field-semantics reference a reader is pointed to — is silent on.

## Why it matters

A reader (human or agent) who asks the `card-schema` skill how the `worker`
field works finds no answer, despite `worker` being a live, validated,
CLI-surfaced field. The skill is the documented contract; the gap is a
self-contradiction between its bundled data and its prose.

## Reachability

Any consumer reading `Skill(card-schema)` for field semantics. The bundled
`schema.yaml` is also inlined into the skill body at install time, so the
declared-but-undocumented mismatch ships to every consumer.

## Fix

Add a short `worker` optional-field subsection to the body, in the established
section style, porting the authoritative spec already written in AGENTS.md
("Card authoring rules → `worker` field"). Single source, single target, single
style — no design decision. The `.claude`/`.codex` mirrors regenerate via the
sync hook and the OpenClaw copy via the port script.

## Not a duplicate

Closest is `card-schema-skill-bundled-schema-omits-supersedes-superseded-by-and-worker`
(**done**) — that card was scoped to the bundled `schema.yaml` **data shape**
(it added `worker` to `optional_fields` and a parity test) and explicitly
deferred the body-prose documentation to "a separate doc-only card." This is
that deferred card. The supersedes/superseded_by body docs that card also
mentioned already exist (SKILL.md "Replacement axis"), leaving `worker` as the
sole remaining body omission. No other `worker`-titled card touches SKILL.md
body docs — they concern engine behavior (filters, auto-populate, board
truncation, validate) or the schema.yaml data parity.

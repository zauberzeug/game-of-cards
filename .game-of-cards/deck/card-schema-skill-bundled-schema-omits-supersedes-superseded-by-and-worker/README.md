---
title: card-schema-skill-bundled-schema-omits-supersedes-superseded-by-and-worker
summary: "The card-schema skill bundles a copy of `schema.yaml` at `goc/templates/skills/card-schema/schema.yaml`, but it has drifted from the authoritative `goc/schema.yaml`: three optional fields — `supersedes`, `superseded_by`, `worker` — are missing from the skill's `optional_fields` list. The drift is replicated across four downstream mirrors (claude-plugin, codex-plugin, vendored `.claude/skills/`, vendored `.codex/skills/`) by the auto-sync, so every consumer of the bundled schema reference reads the wrong field list. No test enforces parity with the engine schema."
status: done
stage: null
contribution: medium
created: "2026-05-30T10:59:18Z"
closed_at: "2026-05-30T11:03:59Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, api-contract, infra]
definition_of_done: |
  - [x] MECHANICAL: `goc/templates/skills/card-schema/schema.yaml` rewritten so its `optional_fields` list matches `goc/schema.yaml` byte-for-byte (adds `supersedes`, `superseded_by`, `worker`).
  - [x] MECHANICAL: `python scripts/sync_plugin_assets.py` run; the four downstream mirror copies (`claude-plugin/skills/card-schema/schema.yaml`, `codex-plugin/skills/card-schema/schema.yaml`, `.claude/skills/card-schema/schema.yaml`, `.codex/skills/card-schema/schema.yaml`) all match the source-of-truth template byte-for-byte afterwards.
  - [x] TDD: a regression test under `tests/` asserts `goc/schema.yaml` and `goc/templates/skills/card-schema/schema.yaml` agree on `required_fields`, `optional_fields`, all `*_values` enums, `canonical_tags`, `title_pattern`, and `schema_version` — drift in either direction fails the test.
  - [x] PROCESS: `uv run goc validate` clean across the dogfood deck; `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` clean.
worker: {who: "claude[bot]", where: main}
---

# The card-schema skill ships a stale schema reference

## Location

- Authoritative engine schema: [`goc/schema.yaml`](../../../goc/schema.yaml) — read at runtime by `engine.load_schema()` (see `engine.py:124` `SCHEMA_FILE = PACKAGE_DIR / "schema.yaml"`).
- Skill-bundled reference (source-of-truth template): [`goc/templates/skills/card-schema/schema.yaml`](../../../goc/templates/skills/card-schema/schema.yaml).
- Downstream mirrors (auto-synced from the template above by `scripts/sync_plugin_assets.py`):
  - `claude-plugin/skills/card-schema/schema.yaml`
  - `codex-plugin/skills/card-schema/schema.yaml`
  - `.claude/skills/card-schema/schema.yaml`
  - `.codex/skills/card-schema/schema.yaml`

## What's broken

`goc/schema.yaml` lists thirteen `optional_fields`:

```yaml
optional_fields:
  - summary
  - stage
  - closed_at
  - advances
  - advanced_by
  - supersedes
  - superseded_by
  - tags
  - worker
  - waiting_on
  - waiting_until
```

`goc/templates/skills/card-schema/schema.yaml` lists only ten — the
three highlighted ones below are missing:

```yaml
optional_fields:
  - summary
  - stage
  - closed_at
  - advances
  - advanced_by
  # supersedes        ← MISSING
  # superseded_by     ← MISSING
  - tags
  # worker            ← MISSING
  - waiting_on
  - waiting_until
```

Direct diff:

```text
$ diff -u goc/schema.yaml goc/templates/skills/card-schema/schema.yaml
@@ -12,10 +12,7 @@
   - closed_at
   - advances
   - advanced_by
-  - supersedes
-  - superseded_by
   - tags
-  - worker
   - waiting_on
   - waiting_until
```

The same three-field omission is present in all four downstream
mirror copies, confirmed by:

```text
$ for f in claude-plugin/skills/card-schema/schema.yaml \
           codex-plugin/skills/card-schema/schema.yaml \
           .claude/skills/card-schema/schema.yaml \
           .codex/skills/card-schema/schema.yaml; do
    diff -u goc/schema.yaml "$f"
  done
# every diff shows the same `-supersedes / -superseded_by / -worker` deletion
```

The fields were added to `goc/schema.yaml` over the project's history:

- `supersedes` / `superseded_by` were added by commit `16a2d7c`
  ("feat(engine): typed superseded_by/supersedes link + dangling-advances
  warning") with the typed-supersession-link work.
- `worker` was added by commit `05ef402` ("feat: add worker field and
  filter to cards").

Both commits updated `goc/schema.yaml` but did not update the skill
mirror, and no regression test caught the drift.

## Why it matters

The card-schema skill is the **shared vocabulary** that lets agents
and humans collaborate without re-deriving terms each conversation
(per the skill's own opening: "The schema is what makes the deck a
contract instead of a chat thread"). The bundled `schema.yaml` is
the machine-readable face of that contract — installed into every
consumer repo by `goc install` and shipped in every plugin payload.

A reader who consults the skill's bundled `schema.yaml` to learn
which optional fields a card may carry will be told `supersedes`,
`superseded_by`, and `worker` are not valid optional fields. The
runtime validator at `engine.py:1163-1165` iterates `required_fields`
only, so cards using these fields still pass `goc validate` — the
defect is documentation-only — but the reference lies to its
consumers.

Compounding the omission, the skill body
(`goc/templates/skills/card-schema/SKILL.md`) **documents
`supersedes` / `superseded_by` extensively** under the "Replacement
axis (supersedes graph)" section (line 652+) but the sibling
`schema.yaml` denies they are valid optional fields — internal
inconsistency between body and bundled data. The `worker` field has
**no documentation in the skill body at all**, and the bundled
`schema.yaml` omits it too — a complete silence on a real frontmatter
field that agents do use (the `_auto_populate_worker` path at
`engine.py:3920-3962` writes it on every `goc status … active`
claim, and `--worker` is a documented `goc new` flag).

Reachability path: any consumer — human, agent, or third-party
tool — that reads `.claude/skills/card-schema/schema.yaml`,
`.codex/skills/card-schema/schema.yaml`, the plugin payload's
`skills/card-schema/schema.yaml`, or the template under
`goc/templates/` itself, gets the stale list. Agents reading the
skill to brief themselves on field semantics (the AUTO-INVOKE
contract on the skill frontmatter explicitly invites this) see
the wrong picture.

## Fix

1. Rewrite `goc/templates/skills/card-schema/schema.yaml` so its
   `optional_fields` list matches `goc/schema.yaml`. The simplest
   form is to copy the canonical file's content verbatim — the two
   files have no intentional divergence today, and the precedent at
   the existing card
   [schema-yaml-omits-closed-at-conditional-requirement-for-terminal-status](../schema-yaml-omits-closed-at-conditional-requirement-for-terminal-status/)
   already treats the template as a strict mirror.
2. Run `python scripts/sync_plugin_assets.py` to propagate to the
   four downstream mirror copies.
3. Add a regression test under `tests/` (e.g.
   `test_skill_schema_yaml_parity.py`) that asserts the canonical
   `goc/schema.yaml` and the template
   `goc/templates/skills/card-schema/schema.yaml` agree on the
   enum-shaped fields (`schema_version`, `required_fields`,
   `optional_fields`, `*_values`, `canonical_tags`, `title_pattern`).
   The plugin-mirror parity check at
   `engine.validate_plugin_mirror_parity()` already enforces that
   the downstream mirrors match the template; this new test closes
   the remaining gap between the template and the engine's
   authoritative copy.

This is intentionally scoped to the data-shape parity. The skill
body's missing `worker` documentation and the body/bundle
disagreement about `supersedes` are downstream consequences of the
same drift; a separate doc-only card can address the body prose
once the bundled reference is correct. The existing card
[schema-yaml-omits-closed-at-conditional-requirement-for-terminal-status](../schema-yaml-omits-closed-at-conditional-requirement-for-terminal-status/)
covers a different drift (`closed_at`'s conditional-requirement
isn't expressible in the current schema shape) and is not
superseded by this one.

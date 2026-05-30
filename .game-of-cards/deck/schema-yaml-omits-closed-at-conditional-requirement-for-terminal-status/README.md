---
title: schema-yaml-omits-closed-at-conditional-requirement-for-terminal-status
summary: "`goc/schema.yaml` lists `closed_at` in `optional_fields`, implying it is freely optional. The validator at `engine.py:1206-1215` actually enforces it as **conditionally required**: must be set when `status` ∈ {done, disproved, superseded}, must be null otherwise. The schema doesn't model conditional-requiredness, so the authoritative spec under-describes the constraint and the rule lives only in code."
status: open
stage: null
contribution: medium
created: "2026-05-30T03:35:28Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [documentation, api-contract]
definition_of_done: |
  - [ ] PROCESS: option A (doc-only), B (conditional-requirements vocabulary), or C (per-field mapping) decided and recorded in `log.md` with rationale before any code change.
  - [ ] MECHANICAL: `goc/schema.yaml` updated so `closed_at`'s conditional requirement is legible from the file alone (no need to read `engine.py` to learn the rule).
  - [ ] MECHANICAL: `goc/templates/skills/card-schema/schema.yaml` updated to match (the inlined skill mirror that ships to consumers).
  - [ ] TDD: a regression test asserts the schema declaration and the `validate_card` rule for `closed_at` agree — drift in either direction fails the test.
  - [ ] PROCESS: `uv run goc validate` clean across the dogfood deck; `uv run python -m unittest discover -s tests` green.
---

# `schema.yaml` omits `closed_at`'s conditional requirement for terminal status

## Location

- Schema declaration: [`goc/schema.yaml:9-20`](../../../goc/schema.yaml) — `closed_at` is listed flat under `optional_fields:`.
- Validator rule (code): [`goc/engine.py:1205-1215`](../../../goc/engine.py) — conditional-required rule for terminal statuses.
- Mirrored copy: [`goc/templates/skills/card-schema/schema.yaml:9-20`](../../../goc/templates/skills/card-schema/schema.yaml) — same drift in the inlined skill copy.

## What's broken

`schema.yaml` declares two flat field categories:

```yaml
required_fields:
  - title
  - status
  - contribution
  - created
  - human_gate
  - definition_of_done
optional_fields:
  - summary
  - stage
  - closed_at      # ← listed as plain-optional
  - advances
  ...
```

The validator iterates `required_fields` at `engine.py:1163-1165` and
flags any field missing from frontmatter. `optional_fields` is loaded
into the `Schema` dataclass (`engine.py:387-409`) but **never
consulted** at validation time — it is purely documentary.

Then `engine.py:1205-1215` applies an additional, hard-coded constraint
that contradicts the "optional" framing:

```python
status_value = fm.get("status")
if status_value in TERMINAL_STATUSES:
    if closed_at is None:
        errors.append(f"{t.title}: closed_at: must be set when status={status_value}")
    if status_value == "done" and t.dod_open > 0:
        errors.append(f"{t.title}: definition_of_done: status=done with {t.dod_open} unchecked boxes")
elif closed_at is not None:
    errors.append(
        f"{t.title}: closed_at: must be null when status is non-terminal"
        f" (status={status_value!r}, closed_at={closed_at!r})"
    )
```

`TERMINAL_STATUSES = frozenset({"done", "disproved", "superseded"})`
(`engine.py:1695`).

So `closed_at` is in fact:

- **Required** when `status` ∈ {done, disproved, superseded}.
- **Forbidden** (must be `null`) when `status` ∈ {open, active, blocked}.

Neither shape is captured anywhere in `schema.yaml`. The
"conditionally required" semantic lives only in the validator body.

The skill body at
[`goc/templates/skills/card-schema/SKILL.md:123-128`](../../../goc/templates/skills/card-schema/SKILL.md)
*does* describe the symmetric rule in prose:

> `closed_at` is stamped on **every terminal exit** ... Validator
> rule is symmetric: `closed_at` is required ...

— but the machine-readable `schema.yaml` shipped next to it
contradicts that prose by listing `closed_at` as plain-optional.

## Empirical evidence

Adding a terminal status with no `closed_at` to a card and running
`goc validate` produces the conditional-required error, despite the
schema listing the field as optional:

```
$ # synthesized card with status: done, closed_at omitted
$ uv run goc validate
<title>: closed_at: must be set when status=done
```

Schema readers (humans writing tools, external contributors, or the
inlined `card-schema` skill mirror that ships to consumers) cannot
derive that rule from `schema.yaml` alone.

## Why it matters

1. **Authoritative-spec drift.** `schema.yaml` is the only data-format
   declaration that ships with the package. The skill body, the
   validator code, and the dogfood deck all reference it as the
   contract. Listing a conditionally-required field as plain-optional
   makes the spec wrong, full stop.

2. **The mirrored copy compounds the drift.**
   `goc/templates/skills/card-schema/schema.yaml` ships the same
   drift to every consumer install, embedded into the
   `card-schema` skill body.

3. **No automated guard.** Because `optional_fields` is purely
   documentary (the engine loads it into a dataclass field but never
   reads it after that), there is no tripwire that fires when the
   list drifts. The `record-closure-date-for-disproved-and-superseded-cards`
   card (done 2026-05-14) updated the validator and three skill
   bodies — its DoD did not include `schema.yaml`, which is why the
   drift survived.

4. **Reachability.** Any user reading `schema.yaml` to write external
   tooling (a non-`goc` validator, a card-importer, a deck migration
   script) will produce non-validating frontmatter on the terminal-
   exit paths. The schema reader who follows the spec literally is
   the failure case.

## Decision required

`closed_at` is the immediate problem, but the underlying gap is that
`schema.yaml` has no vocabulary for **conditional requiredness keyed
on another field's value**. Three credible fix paths, each with a
different surface area:

### Option A — Documentary-only: add a `closed_at` block with prose

Keep `optional_fields` flat. Add a `closed_at:` block (or top-level
key) to `schema.yaml` that documents the rule as comment / prose:

```yaml
optional_fields:
  - summary
  - stage
  # closed_at is conditionally required: must be set when status is
  # terminal (done/disproved/superseded), must be null otherwise.
  # See engine.py validate_card for the enforced rule.
  - closed_at
  ...
```

- **Pro**: minimal change; no validator work; no schema-shape break.
- **Con**: still requires the validator's hardcoded rule; external
  schema readers have to parse YAML comments (which most YAML loaders
  drop). The rule is still in code, not data.

### Option B — Data-model the rule: extend the schema vocabulary

Introduce a new top-level section (or per-field shape) that captures
the constraint as data:

```yaml
conditional_requirements:
  - field: closed_at
    required_when:
      status: [done, disproved, superseded]
    forbidden_otherwise: true
```

Wire `validate_card` to interpret this section instead of hardcoding
the rule. Move `closed_at` out of `optional_fields` (or add a
back-reference). The conditional-requirement vocabulary is reusable —
e.g. `superseded_by` could declare `required_when: status: superseded`.

- **Pro**: rule lives in data; external readers can interpret it; the
  schema becomes the single source of truth.
- **Con**: introduces a new schema shape; needs a migration story;
  the validator's enum-style branching grows.

### Option C — Per-field metadata: switch to a mapping shape

Replace `optional_fields:` (list of strings) with a mapping where
each field carries its constraint metadata:

```yaml
fields:
  closed_at:
    required: conditional
    required_when_status: [done, disproved, superseded]
  summary:
    required: false
  title:
    required: true
```

- **Pro**: every field's contract is co-located; extensible to other
  metadata (deprecation, default, etc.).
- **Con**: larger surface change; `schema_version` bump; breaks any
  consumer that parses `optional_fields` / `required_fields` as
  lists today.

A human pick is needed because the right answer depends on whether
the project wants `schema.yaml` to evolve into a richer data-driven
spec (B/C) or stay a thin doc surface with rules in code (A).

## Fix

Pending the decision above. Whichever option lands, both
`goc/schema.yaml` AND
`goc/templates/skills/card-schema/schema.yaml` must be updated (the
second is the inlined skill copy that ships to consumers). A
`goc validate` self-check or `pre-commit` guard should be added so
the drift cannot recur silently — the existing
`scripts/sync_plugin_assets.py --check` already enforces the mirror
parity for the skill copy, but nothing enforces "the validator rule
matches the schema declaration."

## Dedup

- [closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter](../closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter/) (done 2026-05-29) — different defect: about the *string format* of `closed_at` values, not its requiredness.
- [record-closure-date-for-disproved-and-superseded-cards](../record-closure-date-for-disproved-and-superseded-cards/) (done 2026-05-14) — implemented the conditional-required rule in the validator but did not update `schema.yaml`. This card is the doc-drift remainder.
- [next-card-impact-ladder-references-nonexistent-frontmatter-field](../next-card-impact-ladder-references-nonexistent-frontmatter-field/) (done) — different surface: skill body referenced a non-existent field. Here the field exists; its constraint is mis-declared.

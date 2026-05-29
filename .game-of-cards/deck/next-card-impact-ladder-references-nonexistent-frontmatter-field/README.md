---
title: next-card-impact-ladder-references-nonexistent-frontmatter-field
summary: "`next-card`'s Impact ladder section documents `impact: high | medium | low` as a frontmatter field, but the schema declares `contribution` and no `impact` field exists in `schema.yaml` or the engine. A filer following the example writes a card the validator rejects (missing required `contribution`) or silently accepts as junk."
status: done
stage: null
contribution: high
created: "2026-05-29T11:56:14Z"
closed_at: "2026-05-29T12:01:20Z"
human_gate: none
advances: []
advanced_by:
  - skill-prose-still-calls-queue-impact-sorted-after-impact-contribution-rename
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (the four documented `impact:` field-name occurrences in `goc/templates/skills/next-card/SKILL.md` are gone; every documented field name resolves against `schema.yaml`)
  - [x] MECHANICAL: `goc/templates/skills/next-card/SKILL.md:49-61` renamed from "Impact ladder" → "Contribution ladder", with `impact: high|medium|low` rewritten to `contribution: high|medium|low`
  - [x] MECHANICAL: `goc/templates/skills/pull-card/SKILL.md:123` "picked because impact:high" example replaced with `contribution:high` so the bad-pattern callout doesn't propagate the wrong field name
  - [x] MECHANICAL: `scripts/sync_plugin_assets.py` regenerates `.claude/skills/`, `.codex/skills/`, `claude-plugin/skills/`, `codex-plugin/skills/` mirrors of next-card and pull-card; `python scripts/sync_plugin_assets.py --check` exits zero
  - [x] PROCESS: `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# next-card-impact-ladder-references-nonexistent-frontmatter-field

## Location

- `goc/templates/skills/next-card/SKILL.md:49-61` — the "Impact ladder" section.
- `goc/templates/skills/pull-card/SKILL.md:123` — bad-pattern example uses `impact:high`.
- Schema source of truth: `goc/schema.yaml:24` declares `contribution_values: [high, medium, low]`. No `impact` key appears anywhere in `schema.yaml`.
- Engine sort: `goc/engine.py:1697` `CONTRIBUTION_ORDER = {"high": 0, "medium": 1, "low": 2}`; `goc/engine.py:1806` `CONTRIBUTION_RANK = {"high": 9.0, "medium": 3.0, "low": 1.0}`; `goc/engine.py:1878` `own = CONTRIBUTION_RANK.get(t.contribution, 0.0)`.

## What's broken

`next-card` is the autonomous-loop picker — every `/loop pull-card` invocation reads this skill body. Its "Impact ladder" section literally names a frontmatter field that does not exist:

From `goc/templates/skills/next-card/SKILL.md:49-61`:

```
### Impact ladder

`high` outranks `medium` outranks `low`. Tags refine:

- **`impact: high`** — wrong algorithm vs. cited literature, silent
  state corruption, broken public API, default config that
  contradicts the science. Doc claims that contradict an authoritative
  source — `tags: [documentation]` + `impact: high` is the high-impact
  doc-quality slot. Treat these as load-bearing.
- **`impact: medium`** — tolerance creep, vacuous assertions, tests
  that pass for the wrong reason, missing guard rails.
- **`impact: low`** — README pinned-metric stale, docstring documents
  removed flag, stale references.
```

But `goc/schema.yaml:1-25` (the schema, source of truth) declares:

```yaml
required_fields:
  - title
  - status
  - contribution      # ← the real field
  - created
  - human_gate
  - definition_of_done
...
contribution_values:  [high, medium, low]
```

And every other skill uses `contribution` correctly:

- `goc/templates/skills/card-schema/SKILL.md:198-204` — "The `contribution` field declares atomic per-card value …"
- `goc/templates/skills/audit-deck/SKILL.md:68-70` — "Doc claims that contradict an authoritative source are `contribution: high` + `tags: [documentation]`, NOT low."
- `goc/templates/skills/create-card/SKILL.md:134` — the canonical scaffold command uses `--contribution`.

Only `next-card` drifts to `impact:`. `pull-card/SKILL.md:123` mentions `impact:high` in a "Don't narrate" example — quoted as the bad pattern but propagates the wrong field name into the next reader's vocabulary.

## Empirical evidence

`reproduce.py` output (run via `uv run python deck/<title>/reproduce.py`):

```
schema known fields:
  required: ['title', 'status', 'contribution', 'created', 'human_gate', 'definition_of_done']
  optional: ['summary', 'stage', 'closed_at', 'advances', 'advanced_by', 'supersedes', 'superseded_by', 'tags', 'worker', 'waiting_on', 'waiting_until']
  contribution_values: ['high', 'medium', 'low']
  has 'impact' anywhere in schema.yaml? False

next-card SKILL.md occurrences of 'impact: <level>' (drift):
  L53:   - **`impact: high`** — wrong algorithm vs. cited literature, silent
  L56:     source — `tags: [documentation]` + `impact: high` is the high-impact
  L58:   - **`impact: medium`** — tolerance creep, vacuous assertions, tests
  L60:   - **`impact: low`** — README pinned-metric stale, docstring documents

pull-card SKILL.md occurrences of 'impact:<level>' (propagated example):
  L123:   because impact:high". The commit message and closure log already say

card filed with impact: high and no contribution:
  validate errors: ['probe-impact-field-card: contribution: required field missing']

card filed with BOTH impact: high AND contribution: high:
  validate errors (clean): True
  computed value uses contribution=high (rank 9.0): True
  the impact field is silently accepted dead weight.

FAIL: next-card SKILL.md documents 4 `impact:` field-name occurrences but the schema has no `impact` field.
```

## Why it matters

`Skill(next-card)` is load-bearing for autonomous mode. `pull-card` calls `next-card` indirectly via the `--ready` queue, but more importantly the skill body itself is the first thing an LLM reads when asked "what should I work on?" — it teaches both human filers and LLM filers a wrong frontmatter field name.

**Reachability path**: an LLM following `next-card`'s example to file a new card will write `impact: high` instead of `contribution: high`. Two failure modes:

1. **Validator rejects it.** `goc/engine.py:1164-1166` requires `contribution`; missing → `contribution: required field missing` (verified in `reproduce.py`). The LLM is confused — the skill it just read said to use `impact`, but the validator demands `contribution`. The two messages can only be reconciled by reading source code.
2. **LLM sets both fields defensively.** `impact` is silently accepted (the validator only checks known fields by name — unknown frontmatter keys never error; see `goc/engine.py:1164-1267`). The `impact` field becomes dead weight in every new card. `CONTRIBUTION_RANK.get(t.contribution, 0.0)` at `engine.py:1878` ignores `impact`, so the sort still uses `contribution`.

The defect is documentation drift, but it lives in the skill that the autonomous loop reads on every pull. It also primes future audit-deck rounds to surface the same finding repeatedly until someone fixes it.

## Fix

Mechanical rename in two files:

**`goc/templates/skills/next-card/SKILL.md:49-61`:**

```diff
-### Impact ladder
+### Contribution ladder

 `high` outranks `medium` outranks `low`. Tags refine:

-- **`impact: high`** — wrong algorithm vs. cited literature, silent
+- **`contribution: high`** — wrong algorithm vs. cited literature, silent
   state corruption, broken public API, default config that
   contradicts the science. Doc claims that contradict an authoritative
-  source — `tags: [documentation]` + `impact: high` is the high-impact
+  source — `tags: [documentation]` + `contribution: high` is the high-impact
   doc-quality slot. Treat these as load-bearing.
-- **`impact: medium`** — tolerance creep, vacuous assertions, tests
+- **`contribution: medium`** — tolerance creep, vacuous assertions, tests
   that pass for the wrong reason, missing guard rails.
-- **`impact: low`** — README pinned-metric stale, docstring documents
+- **`contribution: low`** — README pinned-metric stale, docstring documents
   removed flag, stale references.
```

**`goc/templates/skills/pull-card/SKILL.md:123`:**

```diff
-because impact:high". The commit message and closure log already say
+because contribution:high". The commit message and closure log already say
```

Then run `python scripts/sync_plugin_assets.py` to regenerate the four mirror trees (`.claude/`, `.codex/`, `claude-plugin/`, `codex-plugin/`), and `python scripts/port_skills_to_openclaw.py` for the OpenClaw port. Pre-commit will auto-stage the mirrors; the OpenClaw port is reviewed and committed by hand.

Lines that use "impact" as English (e.g. line 21's "impact-sorted queue", line 45's "sorted by impact desc", line 137's "rationale — impact") are colloquial, not field-name references, and can stay — though renaming line 45 to "contribution desc" is consistent. Leave that as a polish call for the fixer.

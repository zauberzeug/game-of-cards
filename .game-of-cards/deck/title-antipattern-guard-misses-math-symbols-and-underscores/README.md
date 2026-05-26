---
title: title-antipattern-guard-misses-math-symbols-and-underscores
summary: "The `card-schema` skill documents a 7-row title-antipattern table whose final row is `Math symbols` with the tailored remedy `Use words (gte, at-least)`, and claims `goc new rejects titles matching any of these antipatterns`. But `TITLE_ANTIPATTERNS` has only 6 patterns and none match math symbols or a bare underscore, so those titles fall through the antipattern guard to the generic regex error — the exact unhelpful-message failure mode the closed card `title-guard-shows-regex-error-instead-of-helpful-suggestion` was meant to eliminate. Confirmed end-to-end: `goc new late-hr-≥-half` and `goc new my_first_card` both print the bare regex error."
status: done
stage: null
contribution: low
created: "2026-05-26T22:25:59Z"
closed_at: 2026-05-26T23:11:00Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation, api-contract]
definition_of_done: |
  - [x] TDD: `goc new "late-hr-≥-half"` and `goc new "my_first_card"` print a tailored antipattern message naming the remedy (e.g. "Use words (gte, at-least)" / "lower-kebab; underscores aren't allowed"), not the bare `does not match '^[a-z0-9]...'` regex error
  - [x] TDD: `_check_title_antipatterns("late-hr-≥-0.5")` and `_check_title_antipatterns("my_first_card")` each return a non-empty reason list
  - [x] MECHANICAL: the `card-schema` skill's antipattern table and `TITLE_ANTIPATTERNS` agree row-for-row (the doc's 7th "Math symbols" row has a matching code pattern; underscore is covered by either a doc row + pattern or the existing `_md_`/`_py_` row is generalized)
  - [x] PROCESS: plugin/skill mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green) since the card-schema skill body is mirrored; `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# title-antipattern-guard-misses-math-symbols-and-underscores

## Location

- Doc side: `goc/templates/skills/card-schema/SKILL.md:758` — the
  antipattern table's final row.
- Doc claim: `goc/templates/skills/card-schema/SKILL.md:748`.
- Code side: `goc/engine.py:3505-3512` — `TITLE_ANTIPATTERNS`.
- Guard ordering: the antipattern check (`_check_title_antipatterns`,
  `goc/engine.py:3515`) runs before the `title_pattern` regex gate.

## What's broken

The skill documents a tailored antipattern message for math-symbol titles
(`goc/templates/skills/card-schema/SKILL.md:758`):

```
| Math symbols (`Δ`, `≤`, `²`, `√`, `±`) | `late-hr-≥-0.5` | Use words (`gte`, `at-least`); the slug pattern allows `[a-z0-9-]` only |
```

and asserts (`SKILL.md:748`):

> `goc new` rejects titles matching any of these antipatterns:

But `TITLE_ANTIPATTERNS` (`goc/engine.py:3505-3512`) has only six patterns —
`rN`, `path-N`, `phase-N`, `bug-N`, `_md_`/`_py_`, and camelCase. None
matches a math symbol, and none matches a bare underscore outside the
`_md_`/`_py_` infix. So a math-symbol or underscore title skips the
antipattern guard entirely and is rejected only by the generic regex gate
with no remedy hint — the exact failure mode the closed card
[title-guard-shows-regex-error-instead-of-helpful-suggestion](../title-guard-shows-regex-error-instead-of-helpful-suggestion/)
set out to eliminate (it fixed `_md_`/camelCase reachability and the guard
ordering, but never added the math-symbol/underscore rows the doc table
already promises).

## Empirical evidence

```
$ uv run goc new "late-hr-≥-half"
ERROR: title 'late-hr-≥-half' does not match '^[a-z0-9][a-z0-9-]*[a-z0-9]$'
$ uv run goc new "my_first_card"
ERROR: title 'my_first_card' does not match '^[a-z0-9][a-z0-9-]*[a-z0-9]$'
```

Both exit 2 with the bare regex error — not the documented
"Use words (`gte`, `at-least`)" antipattern remedy.

## Why it matters

The doc table is a promise to the card author that bad titles get an
actionable message. For the two most likely accidental inputs (a math
operator pasted from a metric name, or a Python-style `snake_case` slug),
the promise is unmet — the author sees a regex they must decode. Low
blast radius (titles are still rejected, just unhelpfully), but it
re-opens the precise UX regression a prior card already closed.

## Fix

Add patterns to `TITLE_ANTIPATTERNS` so the guard fires its tailored
message before the regex gate:

- a math/non-ASCII-symbol pattern (e.g. any char outside `[a-z0-9-]` that
  is not whitespace) with the remedy "use words — the slug allows
  `[a-z0-9-]` only";
- an underscore pattern (`_`) with the remedy "lower-kebab the intent;
  underscores aren't allowed" (generalizing the existing `_md_`/`_py_`
  row, or adding a sibling row).

Then reconcile the doc table so its row count matches the code (add an
explicit underscore row if one is introduced). Re-sync the mirrored
card-schema skill body.


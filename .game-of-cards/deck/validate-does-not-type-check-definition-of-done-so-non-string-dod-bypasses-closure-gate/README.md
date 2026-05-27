---
title: validate-does-not-type-check-definition-of-done-so-non-string-dod-bypasses-closure-gate
summary: "`validate_card` type-checks `tags` (must be a list) but never checks that `definition_of_done` is a string. A card hand-edited to `definition_of_done: []` or `null` validates clean, `count_dod_boxes` returns (0,0) → `dod_freeform` True, so the closure gate treats it as prose and lets `goc done --force` close it with zero verified criteria."
status: done
stage: null
contribution: medium
created: "2026-05-27T13:27:23Z"
closed_at: 2026-05-27T13:36:09Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py shows a card with `definition_of_done: []` (or `null`) passing `goc validate` today, then failing it after the fix
  - [x] MECHANICAL: `validate_card` rejects a non-string `definition_of_done` with a clear message (mirroring the existing `tags: must be a list` check)
  - [x] PROCESS: drop the `unverified` tag once the reproduce.py lands and confirms the gap
worker: {who: "claude[bot]", where: main}
---

# `goc validate` never type-checks `definition_of_done`; a non-string DoD bypasses the closure gate

> **Resolved 2026-05-27.** Verified by `reproduce.py` (exit 1 before fix, 0
> after) and fixed in `validate_card`. See "Fix (applied)" below.

## Hypothesis (file:line)

`validate_card` (`goc/engine.py:1142`) validates the *type* of several
frontmatter fields — notably `tags`:

```python
tags = fm.get("tags") or []
if not isinstance(tags, list):
    errors.append(f"{t.title}: tags: must be a list")
```

— but it never type-checks `definition_of_done`. The required-field loop
(`engine.py:1146-1148`) only checks presence, not type.

`count_dod_boxes` (`goc/engine.py:555-558`) returns `(0, 0)` for any
non-string:

```python
def count_dod_boxes(dod_field: str) -> tuple[int, int]:
    if not isinstance(dod_field, str):
        return 0, 0
    return len(DOD_OPEN_BOX.findall(dod_field)), len(DOD_DONE_BOX.findall(dod_field))
```

`(0, 0)` makes `dod_freeform` True (`engine.py:479-480`:
`return self.dod_open == 0 and self.dod_done == 0`). `_cmd_done`
(`engine.py:2991`: `if t.dod_freeform and not force:`) then routes such a
card to the "free-form prose DoD — pass `--force`" path. And the
`status=done` validation (`engine.py:1189`) only fires when `t.dod_open > 0`,
which is 0 for a non-string DoD — so a *done* card with `definition_of_done: []`
also validates clean.

## Why it matters

The Definition-of-Done checkboxes are the closure contract that AGENTS.md and
`Skill(finish-card)` treat as the closure agreement. A card whose
`definition_of_done` is accidentally (or deliberately) a list, mapping, or
`null` slips through `goc validate` and can be closed with `goc done --force`
having verified nothing — and an already-`done` card in that shape passes
validation rather than being flagged. The type confusion is silent. Impact is
bounded by requiring a hand-edit to a wrong type (the CLI scaffolds a string
DoD), hence `medium` and `unverified` rather than a confirmed high.

## Falsification recipe

1. Scaffold a card, then hand-edit its frontmatter to `definition_of_done: []`.
2. `uv run goc validate` → today prints `OK` for that card (defect present).
   After the fix it should print `definition_of_done: must be a string`.
3. Repeat with `definition_of_done: null` and with `status: done` +
   `definition_of_done: []` + a `closed_at` — confirm the done-with-unchecked
   guard does not catch it today.

If `goc validate` already rejects any of these, the hypothesis is wrong →
flip to `disproved` with the rebuttal recorded in `log.md`.

## Fix (applied)

A type check alongside the `tags` one in `validate_card`:

```python
if "definition_of_done" in fm and not isinstance(fm["definition_of_done"], str):
    errors.append(f"{t.title}: definition_of_done: must be a string")
```

Differs from the original proposal (`dod is not None and ...`): because
`definition_of_done` is a *required* field, a present-but-`null` value is
exactly the bypass the card describes, so the applied check rejects any
non-string present value (`null`, `[]`, mappings, ints) rather than exempting
`None`. The required-field loop still handles a fully-absent field.

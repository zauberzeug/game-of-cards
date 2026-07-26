---
title: mutate-frontmatter-field-append-truncates-final-keep-block-scalar
summary: "When mutate_frontmatter_field appends an absent field and the card's last frontmatter field is a `|+` keep block scalar, the append branch splices the new `field: value` line between the scalar's content and its trailing blank run, so the keep scalar silently reads back one blank line short. `goc validate` passes before and after — fully silent data loss, reachable from `goc status <title> active` on any worker-less card of that shape. Mirror-image cosmetic defect: remove_frontmatter_field on the final field leaves the orphaned blank run behind."
status: open
stage: null
contribution: medium
created: "2026-07-23T01:35:22Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero before the fix (data loss shown) and continues to exit zero after — but with the summary round-tripping byte-identical (`'…\n\n'` before AND after) and the appended `worker` line landing below the keep scalar's blank run, its "NOT REPRODUCED" branch flipped to the pass condition.
  - [ ] TDD: a unittest under `tests/` asserts the invariant for the chosen path (see `## Decision required`): appending an absent field to frontmatter whose final field is a `|+` keep scalar leaves every existing field's parsed value byte-identical.
  - [ ] MECHANICAL: the sibling cosmetic defect is checked either way — `remove_frontmatter_field` on the final field leaves no stray blank-line run — and the verdict (fixed here or explicitly out of scope) is recorded in log.md.
  - [ ] PROCESS: cross-referenced as the fourth `mutate_frontmatter_field` splice defect on the three open siblings' bodies (backslash template, flat-field blank-line over-consume, internal-blank block truncation); if a family meta-fix card is filed instead, this card's fix folds into it via an `advances` edge.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# mutate_frontmatter_field's field-absent append truncates a final `|+` keep block scalar

## Summary

When the mutated field is absent and the card's last frontmatter field is a
`|+` keep block scalar, the append branch splices `field: value` between the
scalar's content and its trailing blank run (which lives in
`FRONTMATTER_RE` group(2) and is re-attached *after* the appended line), so
the keep scalar silently reads back one blank line short. `goc validate`
passes before and after — fully silent data loss, reachable from
`goc status <title> active` on any worker-less card of that shape.

## Location

- `goc/engine.py:486-488` — the field-absent append:

  ```python
  if not pattern.search(fm_text):
      # Field absent — append at the end of the frontmatter block.
      fm_text = fm_text.rstrip() + f"\n{field_name}: {new_value}"
  ```

  then `goc/engine.py:491` re-attaches the blank run *after* the new line:

  ```python
  return f"---\n{fm_text}{trailing}---\n{body}"
  ```

- `goc/engine.py:155-160` — the contract being violated: `FRONTMATTER_RE`'s
  `(\n+)` group exists "so that yaml_lite — not the delimiter — decides
  their fate (a `|+` keep scalar must retain its trailing blank line…)".
  The append branch hands that blank run to the appended flat field
  instead, where yaml_lite ignores it.
- Sibling cosmetic defect: `remove_frontmatter_field`
  (`goc/engine.py:496-515`) removing the *final* field leaves the orphaned
  blank run behind (stray blank line before `---`), the mirror image of the
  same group(2) ownership confusion.

## Empirical evidence

`uv run python .game-of-cards/deck/mutate-frontmatter-field-append-truncates-final-keep-block-scalar/reproduce.py`:

```
summary before mutation: 'ends with a blank line.\n\n'
mutated file:
---
title: t
summary: |+
  ends with a blank line.
worker: {who: probe, where: main}

---
body

summary after mutation:  'ends with a blank line.\n'
DEFECT REPRODUCED: appended field wedged inside the keep scalar's trailing blank run; scalar silently lost its final newline
```

## Why it matters

Reachability: `goc status <title> active` on a card without a `worker`
field appends one via `_auto_populate_worker` (`goc/engine.py:5221`) — the
routine claim step every pull-card session performs. `goc done` /
`goc status <t> disproved|superseded` append `closed_at` the same way on
hand-authored cards lacking the key (`goc/engine.py:4270`, `5310`). The
precondition — a `|+` keep scalar as the *final* frontmatter field — is the
exact shape the closed cards
[frontmatter-re-drops-trailing-blank-line-of-final-keep-block-scalar](../frontmatter-re-drops-trailing-blank-line-of-final-keep-block-scalar/)
and the emitter keep fixes were filed to protect; this is the un-filed
third site of that invariant, and the fourth splice defect in
`mutate_frontmatter_field` after
[mutate-frontmatter-field-corrupts-backslashes-via-regex-replacement-template](../mutate-frontmatter-field-corrupts-backslashes-via-regex-replacement-template/),
[mutate-frontmatter-field-over-consumes-blank-line-after-a-flat-field](../mutate-frontmatter-field-over-consumes-blank-line-after-a-flat-field/), and
[mutate-frontmatter-field-truncates-block-fields-with-internal-blank-lines](../mutate-frontmatter-field-truncates-block-fields-with-internal-blank-lines/)
(all three cover the *replace* path; this is the *append* path).

## Decision required

1. **Append below the blank run** — emit
   `f"---\n{fm_text}{trailing}{field_name}: {new_value}\n---\n{body}"` so
   the keep scalar keeps its blank line and the new field lands after it.
   Correctness depends on yaml_lite attributing a mid-frontmatter blank
   line followed by a column-0 key to the preceding keep scalar — must be
   verified against the parser (the internal-blank sibling card shows this
   area is subtle).
2. **Fold into a family meta-fix** — this is the fourth confirmed splice
   defect in one ~40-line function; instead of a fourth point patch,
   rebuild `mutate_frontmatter_field` / `remove_frontmatter_field` on a
   shared field-extent scanner that owns block-scalar and blank-line
   semantics once (the shape the open drift meta-fix cards prescribe for
   the emitter/parser pairs).

Option 1 is a two-line diff but extends the whack-a-mole series; option 2
is the structural answer and should supersede the three open siblings'
individual fixes if chosen.

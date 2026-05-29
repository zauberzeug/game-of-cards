---
title: mutate-frontmatter-field-over-consumes-blank-line-after-a-flat-field
summary: "The continuation pattern in `mutate_frontmatter_field` was widened with `\\n(?=[ \\t]|\\n)` to keep internal blank lines of a block field. It has no \"inside a block field\" guard, so mutating a FLAT field (`status`, `worker`, `closed_at`) that is immediately followed by a blank line consumes that blank line — and any indented line after it — into the match and deletes it. This is the regression introduced by the fix for the inverse block-field truncation bug, now firing on the live mutation path."
status: done
stage: null
contribution: medium
created: "2026-05-27T01:18:40Z"
closed_at: "2026-05-27T01:23:58Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — mutating a flat field immediately followed by a blank line preserves the blank line, and a stray indented line after the blank is preserved (no silent loss)
  - [x] TDD: the existing block-field invariant still holds — mutating a block field (e.g. `definition_of_done`) with an internal blank line does NOT orphan its tail (the case from the closed sibling card stays green)
  - [x] MECHANICAL: the continuation pattern in `goc/engine.py` only consumes a blank line when it is genuinely internal to the field being mutated (a following indented continuation line exists), not when it is a structural separator before the next top-level `key:` line
  - [x] MECHANICAL: plugin mirrors synced (`python scripts/sync_plugin_assets.py --check` clean) and `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# `mutate_frontmatter_field` over-consumes a blank line after a flat field

## Location

`goc/engine.py:328-331` — the continuation pattern in `mutate_frontmatter_field`:

```python
pattern = re.compile(
    rf"^{re.escape(field_name)}:[ \t]*[^\n]*(?:\n[ \t]+[^\n]*|\n(?=[ \t]|\n))*",
    re.MULTILINE,
)
```

## What's broken

The `\n(?=[ \t]|\n)` alternative was added by the closed card
[mutate-frontmatter-field-truncates-block-fields-with-internal-blank-lines](../mutate-frontmatter-field-truncates-block-fields-with-internal-blank-lines/)
to keep *internal* blank lines of a **block** field from truncating the
match and orphaning the block's tail. But the clause has no "am I inside
a block field?" guard. It fires whenever the mutated field's value is
followed by a blank line — including the common case where the field is a
plain **flat scalar** (`status`, `worker`, `closed_at`) and the blank line
is a *structural separator*, not part of the field. `pattern.sub(...,
count=1)` then deletes the blank line (and any indented line after it)
along with the field.

The docstring (line 313-316) promises a minimally-invasive replacement
whose whole reason for existing is to avoid touching the rest of the file:

```python
"""Line-anchored regex replacement of `field: <whatever>`.

Handles both single-line fields (`field: value`) and block-style fields
(`field:\n  - item`). Avoids YAML round-trip (which reorders keys).
"""
```

Silently swallowing a blank line — or an indented line — that does not
belong to the mutated field contradicts that contract.

`status`, `human_gate`, `closed_at`, and `worker` are exactly the flat
fields the live verbs mutate (`goc status`, `goc decide`, the claim-time
`worker` auto-populate, the `closed_at` stamp in `goc done`), so this
fires on real card edits whenever such a field is followed by a blank line.

## Why it's the regression, not the original bug

The sibling card fixed the **inverse** failure on **block** fields:
the old pattern `(?:\n[ \t]+[^\n]*)*` *under-consumed* — it stopped at
the first internal blank line and orphaned the block's tail. That fix
was filed `low` and explicitly noted it was *latent* ("no live code path
mutates a multi-line block field"). The widening it introduced now
*over-consumes* on **flat** fields, which ARE mutated today. Same
function, opposite symptom, and this time on the active path.

## Empirical evidence

`reproduce.py` output (see sibling file):

```
CASE1 blank-line loss:
'---\ntitle: foo\nstatus: active\nhuman_gate: none\n---\nbody\n'
blank line preserved: False

CASE2 indented-line loss:
'---\ntitle: foo\nworker: alice\nhuman_gate: none\n---\nbody\n'
stray line preserved: False
```

Case 1: mutating `status` (a flat field) immediately followed by a blank
line drops the blank line. Cosmetic, but a direct contract violation.

Case 2: a `worker` mutation deletes a `  stray: indented` line that
followed the blank — genuine data loss of frontmatter content the field
never owned.

## Fix (applied)

The continuation pattern was restructured so the block tail is a single
optional group that can only *open* with an indented line directly after
the header:

```python
pattern = re.compile(
    rf"^{re.escape(field_name)}:[ \t]*[^\n]*"
    rf"(?:\n[ \t]+[^\n]*(?:\n[ \t]+[^\n]*|\n(?=\n*[ \t]))*)?",
    re.MULTILINE,
)
```

A flat scalar (`status: x`, `worker: y`) followed by a blank line never
enters the continuation group, because the first thing after the header
is not an indented line — so the match stops on the header alone and the
structural blank (and anything past it) is left untouched. Once inside
the block, the blank-line clause `\n(?=\n*[ \t])` absorbs an internal
blank only when a further indented line follows it, so a blank preceding
the next top-level `key:` line still ends the match. Both invariants —
block-field tail preserved (sibling card) and flat-field surroundings
preserved (this card) — hold simultaneously; `reproduce.py` now reports
all three cases correct.

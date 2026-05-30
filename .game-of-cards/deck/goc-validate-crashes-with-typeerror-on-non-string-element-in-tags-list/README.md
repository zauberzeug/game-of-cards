---
title: goc-validate-crashes-with-typeerror-on-non-string-element-in-tags-list
summary: "`validate_card` iterates the `tags` list and tests each element with `tag not in schema.canonical_tags` — a set-membership probe. If an element is a non-string container (e.g. a nested flow-sequence `[a, b]` that the YAML-lite parser accepts as a list inside a list), Python raises `TypeError: unhashable type: 'list'`. `goc validate` aborts with a raw Python traceback instead of emitting the per-card typed error its sibling guards already produce. Same shape as the recently-filed relationship-list peer (`goc-validate-crashes-with-typeerror-on-non-string-element-in-relationship-list`) but on a different field and different code path."
status: open
stage: null
contribution: medium
created: "2026-05-30T05:54:57Z"
closed_at: null
human_gate: decision
advances:
  - bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` writes a card with `tags: [bug, [nested, list]]`, runs `goc validate`, and exits 1 today (raw `TypeError` traceback) and 0 after the fix (clean per-card error).
  - [ ] MECHANICAL: `validate_card` rejects non-string elements in the `tags` field with a typed message ("tags: must be a list of strings; got <type> value=<repr> at index N"), mirroring the existing container-type guard at engine.py:1203 and the relationship-list fix sketch on the peer card.
  - [ ] TDD: a regression test in `tests/` covers a nested-list element AND at least one non-string scalar element (int, null, mapping) on the `tags` field.
  - [ ] EMPIRICAL: `uv run goc validate` on a deck containing such a card prints the typed per-card error and exits non-zero — no Python traceback in the output.
  - [ ] PROCESS: decision recorded — per-site guard (Option 1) vs roll into the shared `_assert_list_of_strings` helper on the meta-fix (Option 2), with rationale.
---

# `goc validate` crashes with `TypeError: unhashable type: 'list'` when a `tags` element is itself a list

## Location

`goc/engine.py:1202-1210` — `validate_card`, the `tags` loop:

```python
tags = fm.get("tags") or []
if not isinstance(tags, list):
    errors.append(f"{t.title}: tags: must be a list")
else:
    for tag in tags:
        if tag not in schema.canonical_tags:        # ← crashes when tag is unhashable
            errors.append(
                f"{t.title}: tags: unknown tag '{tag}' — {_UNKNOWN_TAG_REMEDY}"
            )
```

`schema.canonical_tags` is a `set[str]` (see `Schema.canonical_tags` at
engine.py:400, populated from `schema.yaml` plus
`_load_consuming_repo_tags`).

## What's broken

The outer guard type-checks the *container* (`isinstance(tags, list)`) but
the inner loop assumes each `tag` is a hashable scalar — typically a
known tag string. Python's `in` against a set requires the left operand
to be hashable. Pass a `list` (or `dict`) as an element and
`tag not in schema.canonical_tags` raises
`TypeError: unhashable type: 'list'`, propagating up out of
`validate_card` and out of `_cmd_validate`, where there is no per-card
try/except.

This is the same anti-pattern resolved in adjacent code and the
relationship-list peer card:

- `goc-validate-crashes-with-typeerror-on-non-string-element-in-relationship-list`
  (open, filed 2026-05-30) — same shape, but at `engine.py:1258` for
  `advances` / `advanced_by` / `supersedes` / `superseded_by`.
- `Card.tags` property at `engine.py:521-524` already guards the
  *container* type (`return v if isinstance(v, list) else []`) so
  downstream consumers (`compute_values`, the board renderer, JSON dump)
  see a safe list. The validator is the only consumer that walks the
  raw list without an element-type guard.
- `_load_consuming_repo_tags` (closed family member) guards the
  bare-string scalar shape with an `isinstance(value, list)` check.
- `validate_supersedes_targets` rejects bare-string `supersedes` scalars
  with a typed message.

The relationship-list peer and this card are the two element-type
guard sites; the family otherwise covers container-type and bare-string
shapes.

## Empirical evidence

Captured from a scratch deck written to `/tmp/probe_tags/` on `main`
@ 96c95e1:

```text
$ uv --project /home/runner/work/game-of-cards/game-of-cards run goc validate
Traceback (most recent call last):
  File "/home/runner/work/game-of-cards/game-of-cards/.venv/bin/goc", line 10, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/runner/work/game-of-cards/game-of-cards/goc/cli.py", line 102, in main
    engine_cli(argv)
  File "/home/runner/work/game-of-cards/game-of-cards/goc/engine.py", line 2777, in cli
    _cmd_validate(args)
  File "/home/runner/work/game-of-cards/game-of-cards/goc/engine.py", line 2901, in _cmd_validate
    per = validate_card(t, schema, all_titles)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/game-of-cards/game-of-cards/goc/engine.py", line 1207, in validate_card
    if tag not in schema.canonical_tags:
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: unhashable type: 'list'
```

The offending card has this frontmatter shape:

```yaml
tags: [bug, [nested, list]]
```

A `dict` element repeats the same crash on the same line. A bare scalar
int element (e.g. `tags: [bug, 42]`) survives this line because `42` is
hashable, but the unknown-tag formatter at line 1208 then emits a
slightly misleading message (`unknown tag '42'` rather than `must be a
list of strings`).

## Why it matters

Reachability path: the YAML-lite parser (`goc/engine.py:144`,
`parse_frontmatter` → `yaml.safe_load`) accepts nested flow sequences
inside a block sequence — that's a normal YAML 1.2 shape. Any of:

- a hand-edited card frontmatter the author mistyped (e.g. wrapping a
  tag accidentally),
- a one-shot agent that wrote a card with the wrong list shape,
- a copy-paste from a doc example that used `[a, b]` flow syntax
  inside a longer block list,
- a future emitter regression on `tags` (currently emitted inline by
  `_yaml_inline`, but the field is documented as a list and any change
  to the emitter could shift the shape),

reaches the validator and crashes it. `goc validate` is the deck's
schema-integrity gate (run by `pre-commit`, by CI, by every skill that
needs a clean read). A single malformed card therefore aborts the
entire run with a Python traceback that names a line of `engine.py`,
not the offending card — the deck-wide validator turns into a denial
mechanism instead of a per-card error reporter.

Family signal: the open umbrella card
[bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/)
groups the per-consumer string-vs-list guards. The likely meta-fix when
this card and its relationship-list peer close is to add a shared
`_assert_list_of_strings(field_name, value)` helper that every list-of-
strings consumer (validate_card's tags loop, validate_card's
LIST_REL_FIELDS loop, `_add_to_list_field`, `_remove_from_list_field`,
`_load_consuming_repo_tags`) calls once.

## Decision required

Two credible fix shapes; pick one — same fork as the relationship-list
peer card:

1. **Tighten `validate_card`'s tags loop only.** Add an
   `isinstance(tag, str)` check inside the loop and emit a typed
   message. Smallest diff. Other consumers (e.g. `validate_tag_filters`
   at engine.py:2088, `_cmd_new` at engine.py:4131) receive tags from
   argparse so they're already string-typed; the only at-risk consumer
   is the validator itself.

2. **Promote to a shared `_assert_list_of_strings` helper** and call
   it from both `validate_card.tags` AND
   `validate_card.LIST_REL_FIELDS` (and any other list-of-strings
   consumer surfaced by the meta-fix). Larger diff, closes the family
   for good. This card and the relationship-list peer become two
   instances of the same fix.

The minimal fix unblocks `goc validate` on tags; the shared helper
closes the family. The gate is `decision` because picking option 2
commits the implementer to a small refactor and a coordinated close of
both element-type cards plus the meta-fix.

## Fix (sketch — option 1)

```python
# goc/engine.py around line 1205
tags = fm.get("tags") or []
if not isinstance(tags, list):
    errors.append(f"{t.title}: tags: must be a list")
else:
    for idx, tag in enumerate(tags):
        if not isinstance(tag, str):
            errors.append(
                f"{t.title}: tags: must be a list of strings; "
                f"got {type(tag).__name__} value={tag!r} at index {idx}"
            )
            continue
        if tag not in schema.canonical_tags:
            errors.append(
                f"{t.title}: tags: unknown tag '{tag}' — {_UNKNOWN_TAG_REMEDY}"
            )
```

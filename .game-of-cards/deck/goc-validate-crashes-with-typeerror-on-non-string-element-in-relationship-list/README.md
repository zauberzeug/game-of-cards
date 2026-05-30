---
title: goc-validate-crashes-with-typeerror-on-non-string-element-in-relationship-list
summary: "`validate_card` iterates `LIST_REL_FIELDS` (advances / advanced_by / supersedes / superseded_by) and tests each element with `ref not in all_titles` — a set-membership probe. If an element is a non-string container (e.g. a nested flow-sequence `[a, b]` that the YAML-lite parser accepts as a list inside a list), Python raises `TypeError: unhashable type: 'list'`. `goc validate` aborts with a raw Python traceback instead of emitting the per-card 'must be a list of strings' error its sibling guards (`tags`, `definition_of_done`, `supersedes`-as-scalar) already produce."
status: open
stage: null
contribution: medium
created: "2026-05-30T05:32:23Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: a `reproduce.py` writes a card with `advances: [good, [nested, list]]`, runs `goc validate`, and exits 1 today (raw `TypeError` traceback) and 0 after the fix (clean per-card error)
  - [ ] MECHANICAL: `validate_card` rejects non-string elements in every `LIST_REL_FIELDS` field with a typed message ("must be a list of strings; got <type> at index N"), mirroring the existing `tags` / `supersedes` guards
  - [ ] TDD: a regression test in `tests/` covers a nested-list element AND a non-string scalar element (int, null, mapping) for each of advances / advanced_by / supersedes / superseded_by
  - [ ] EMPIRICAL: `uv run goc validate` on a deck containing such a card prints the typed per-card error and exits non-zero — no Python traceback in the output
  - [ ] PROCESS: drop the `decision` gate to `none` once the fix shape is settled (see `## Decision required` below — likely a one-liner)
---

# `goc validate` crashes with `TypeError: unhashable type: 'list'` when a relationship list element is itself a list

## Location

`goc/engine.py:1250-1259` — `validate_card`, the `LIST_REL_FIELDS` loop:

```python
for field in LIST_REL_FIELDS:
    v = fm.get(field) or []
    if v and not isinstance(v, list):
        errors.append(f"{t.title}: {field}: must be a list")
        continue
    for ref in v:
        if ref == t.title:
            errors.append(f"{t.title}: {field}: self-reference '{ref}'")
        elif ref not in all_titles:                       # ← crashes when ref is unhashable
            errors.append(f"{t.title}: {field}: references unknown title '{ref}'")
```

`LIST_REL_FIELDS = ("advances", "advanced_by", "supersedes", "superseded_by")`
(`goc/engine.py:775`).

## What's broken

The outer guard type-checks the *container* (`isinstance(v, list)`) but
the inner loop assumes each `ref` is a hashable scalar — typically a
title string. Python's `in` against a set requires the left operand to
be hashable. Pass a `list` (or `dict`) as an element and `ref not in
all_titles` raises `TypeError: unhashable type: 'list'`, propagating up
out of `validate_card` and out of `_cmd_validate`, where there is no
per-card try/except.

Compare the recently-shipped sibling guards that produce a typed error
instead of crashing:

- `validate_supersedes_targets` (`goc/engine.py:1295-1302`) rejects a
  bare-string `supersedes` scalar with a typed message — see
  `canonical-tags-loader-iterates-bare-string-scalar-character-by-character`
  and the `_load_consuming_repo_tags` guard added in the same family.
- `validate_card` type-checks `definition_of_done` (added by
  `validate-does-not-type-check-definition-of-done-...`, closed
  2026-05-27) and `tags` (must-be-a-list).

The relationship-list element-type check is the missing peer: it walks
the list but never asks whether each element is a string.

## Empirical evidence

`reproduce.py` (to be committed alongside this card) shows the crash.
Captured by hand from a scratch run on `main` @ 6d017c1:

```text
$ uv run python -m goc.cli validate
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/runner/work/game-of-cards/game-of-cards/goc/cli.py", line 106, in <module>
    main()
  File "/home/runner/work/game-of-cards/game-of-cards/goc/cli.py", line 102, in main
    engine_cli(argv)
  File "/home/runner/work/game-of-cards/game-of-cards/goc/engine.py", line 2777, in cli
    _cmd_validate(args)
  File "/home/runner/work/game-of-cards/game-of-cards/goc/engine.py", line 2901, in _cmd_validate
    per = validate_card(t, schema, all_titles)
  File "/home/runner/work/game-of-cards/game-of-cards/goc/engine.py", line 1258, in validate_card
    elif ref not in all_titles:
TypeError: unhashable type: 'list'
```

The offending card is one with this frontmatter shape:

```yaml
advances:
  - good-target
  - [nested, list]
```

The YAML-lite parser accepts the inline flow sequence as a list element
and surfaces `['good-target', ['nested', 'list']]` to the validator. A
non-string scalar (int, null, mapping) hits the same crash via a
slightly different path (e.g. an int `42` is hashable so it survives
line 1258, but the subsequent emit path or attestation path can fail
on `.startswith` / string ops elsewhere). A `dict` element repeats
the unhashable crash on line 1258.

## Why it matters

Reachability path: the YAML-lite parser (`goc/engine.py:144`,
`parse_frontmatter` -> `yaml.safe_load`) accepts nested flow sequences
inside a block sequence — that's a normal YAML 1.2 shape. Any of:

- a hand-edited card frontmatter the author mistyped,
- a one-shot agent that wrote a card with the wrong list shape,
- a copy-paste from a doc example that used `[a, b]` flow syntax
  inside a longer block list,

reaches the validator and crashes it. `goc validate` is the deck's
schema-integrity gate (run by `pre-commit`, by CI, by every skill that
needs a clean read). A single malformed card therefore aborts the
entire run with a Python traceback that names a line of `engine.py`,
not the offending card — the deck-wide validator turns into a denial
mechanism instead of a per-card error reporter.

This is the same anti-pattern resolved twice already in
recent history:

- `frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror`
  (`goc/engine.py:161`, closed 2026-05-27) — top-level frontmatter is
  a non-mapping.
- `canonical-tags-loader-iterates-bare-string-scalar-character-by-character`
  (closed 2026-05-29) — a bare-string scalar where a list was
  expected.
- `validate-does-not-type-check-definition-of-done-so-non-string-dod-bypasses-closure-gate`
  (closed 2026-05-27) — a non-string `definition_of_done` slips
  past the closure gate.

This card is the relationship-list peer of those guards.

Family signal: the open umbrella card
[bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/)
already groups the per-consumer string-vs-list guards. This finding
extends the family to non-string *elements* (the prior cards covered
the *container* type). The likely meta-fix when this card closes is to
add a `_assert_list_of_strings(field_name, value)` helper that every
LIST_REL_FIELDS consumer calls once, rather than continuing to grow
per-consumer guards.

## Decision required

Two credible fix shapes; pick one:

1. **Tighten `validate_card` only.** Add an `isinstance(ref, str)`
   check inside the LIST_REL_FIELDS loop and emit a typed message.
   Smallest diff. Other consumers (`_cmd_repair_edges`,
   `compute_values`, the half-edge detector) keep their own assumptions
   about element type — they may crash on the same shape if the
   validator is bypassed (e.g. `goc show`, `goc --board`).

2. **Promote to a shared `_assert_list_of_strings` helper** and call
   it from `validate_card` + every other LIST_REL_FIELDS consumer
   (or from `load_card`, fail-fast at parse time). Larger diff,
   eliminates the family for good. Aligned with the meta-fix
   trajectory recorded in
   [bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/).

The minimal fix unblocks `goc validate`; the shared helper closes the
family. The gate is `decision` because picking option 2 commits the
implementer to a small refactor across multiple call sites.

## Fix (sketch — option 1)

```python
# goc/engine.py around line 1255
for ref in v:
    if not isinstance(ref, str):
        errors.append(
            f"{t.title}: {field}: must be a list of strings; "
            f"got {type(ref).__name__} value={ref!r}"
        )
        continue
    if ref == t.title:
        errors.append(f"{t.title}: {field}: self-reference '{ref}'")
    elif ref not in all_titles:
        errors.append(f"{t.title}: {field}: references unknown title '{ref}'")
```

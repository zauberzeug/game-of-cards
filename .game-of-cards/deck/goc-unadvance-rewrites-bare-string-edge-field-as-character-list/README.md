---
title: goc-unadvance-rewrites-bare-string-edge-field-as-character-list
summary: "_remove_from_list_field lacks the isinstance(cur, list) guard its sibling _add_to_list_field has. When goc unadvance acts on a card whose advances / advanced_by / supersedes / superseded_by field was authored (or left by an earlier emitter) as a bare-string scalar, the list comprehension iterates the string character-by-character and rewrites the field to disk as one-character entries."
status: open
stage: null
contribution: medium
created: "2026-05-30T05:24:48Z"
closed_at: null
human_gate: decision
advances:
  - bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — the corrupted character-list rewrite no longer fires
  - [ ] TDD: a regression test in tests/ covers _remove_from_list_field receiving a non-list value (bare string scalar) and asserts the chosen behaviour
  - [ ] PROCESS: decision recorded — per-site isinstance guard mirroring _add_to_list_field, OR rolled into the meta-fix bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
  - [ ] MECHANICAL: chosen guard / coercion lands at engine.py:4180 (or upstream in parse_frontmatter, per the decision above)
  - [ ] PROCESS: log.md records which path was taken and why
---

# goc-unadvance-rewrites-bare-string-edge-field-as-character-list

## Location

`goc/engine.py:4180-4186` — `_remove_from_list_field`.

## What's broken

The two siblings in this helper pair behave asymmetrically. `_add_to_list_field`
explicitly guards against a non-list scalar:

```python
def _add_to_list_field(text: str, field: str, title_to_add: str) -> str:
    """Add title_to_add to a frontmatter list field, idempotent."""
    fm, body = parse_frontmatter(text)
    cur = fm.get(field) or []
    if not isinstance(cur, list):
        raise ValueError(f"{field}: not a list")
    ...
```

`_remove_from_list_field`, written in parallel a few lines below, does not:

```python
def _remove_from_list_field(text: str, field: str, title_to_remove: str) -> str:
    fm, body = parse_frontmatter(text)
    cur = fm.get(field) or []
    if title_to_remove not in cur:
        return text
    fm[field] = [s for s in cur if s != title_to_remove]
    return emit_frontmatter(fm, body=body)
```

When `cur` is a bare string scalar (e.g. `advances: othercard` rather than
`advances: [othercard]` or block-style), two things go wrong:

1. `title_to_remove not in cur` becomes a **substring** test on the string, not
   a membership test on a list. If the title is a substring of `cur`, the
   early-exit is skipped; if it isn't, the function returns silently with the
   bare-string state preserved (no error, no repair).
2. The list comprehension `[s for s in cur if s != title_to_remove]` iterates
   the string **character-by-character**. Each one-character `s` cannot equal a
   multi-character `title_to_remove`, so every character is kept. The field is
   then written back to disk as a per-character list.

## Reachability path

The only caller is `_mutate_pair(..., add=False)` at `engine.py:4198`, which
runs `op` on both the child's and the parent's README. `_mutate_pair(add=False)`
is reached exclusively from `_cmd_unadvance` (engine.py:4418) — the
`goc unadvance <title> --by <advancer>` verb. The fields exercised are
`advanced_by` on the child and `advances` on the parent (see engine.py:4418).

The bare-string-scalar shape reaches frontmatter through the same path
documented on the sibling cards in this family — a hand-authored card, an
earlier emitter that wrote a single-item list as a bare scalar, or a
one-shot tool that produced unquoted YAML. The `bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`
meta-fix card catalogues the input source.

## Empirical evidence

Output of `uv run python deck/goc-unadvance-rewrites-bare-string-edge-field-as-character-list/reproduce.py`:

```
parent advances before: othercard (type: str)
running _remove_from_list_field(parent_text, 'advances', 'othercard')
parent advances after:  ['o', 't', 'h', 'e', 'r', 'c', 'a', 'r', 'd'] (type: list)

FAIL: bare-string 'advances: othercard' was rewritten as a character-list instead of being removed or rejected.
```

## Why it matters

Persistent on-disk corruption is strictly worse than the previously-closed
read-side defects in this family (`tags-property-iterates-bare-string-tags-character-by-character`,
`canonical-tags-loader-iterates-bare-string-scalar-character-by-character`,
`supersedes-and-superseded-by-walkers-iterate-bare-string-scalars-character-by-character`):
those corrupted in-memory reads of a malformed file; this corrupts the file
itself, after which every subsequent read of the field sees the per-character
list as the canonical truth. Recovering means hand-editing the README, since
`goc validate` will happily accept `advances: [o, t, h, e, r, c, a, r, d]`
as a well-formed list whose entries happen to be unknown card titles.

## Decision required

Two credible fix paths; the choice depends on the resolution of the meta-fix
this card advances:

**Option A — per-site guard.** Add `if not isinstance(cur, list): raise
ValueError(f"{field}: not a list")` to `_remove_from_list_field` immediately
after the `cur = fm.get(field) or []` line, mirroring `_add_to_list_field`.
Pro: minimal, matches the existing pattern, ships in one line.
Con: another per-consumer guard, exactly the spawning behaviour the meta-fix
card was opened to stop.

**Option B — fold into the meta-fix.** Resolve `bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`
first (coerce bare-string scalars to single-element lists at
`parse_frontmatter` time, or reject them at parse time and let
`load_card_or_exit` block the operation upstream of `_mutate_pair`). This
card then closes on the meta-fix landing.
Pro: stops the spawning.
Con: blocks on the meta-fix's own decision.

The per-site guard is reversible if the meta-fix later subsumes it; the
inverse is not true.

---
title: migrate-list-style-help-promises-key-order-normalisation-the-emitter-never-does
summary: "The migrate-list-style subparser help and command docstring both list key order among the things a canonical re-emit normalises, but emit_frontmatter iterates the parsed dict in the authored file's own order and never reorders keys. A card whose only drift is key order is reported as already canonical, and the per-card changed-part report can never name key order."
status: done
stage: null
contribution: medium
created: "2026-09-07T04:54:32Z"
closed_at: "2026-09-07T05:03:28Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the promise and the behaviour agree again.
  - [x] MECHANICAL: the `migrate-list-style` subparser help (`goc/engine.py:4137`) no longer names key order among what a canonical re-emit normalises, and enumerates only what `emit_frontmatter` actually owns.
  - [x] MECHANICAL: `_cmd_migrate_list_style`'s docstring (`goc/engine.py:7144`) carries the same corrected scope, plus a one-line note that key order is *preserved* from the authored file, so the next reader does not re-add the claim.
  - [x] TDD: a regression test pins both halves — `emit_frontmatter` round-trips a key-reordered card byte-identically (order preserved), and neither user-facing scope string claims key-order normalisation.
  - [x] MECHANICAL: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; plugin mirrors synced by the pre-commit hook.
worker: {who: "claude[bot]", where: main}
---

# migrate-list-style promises key-order normalisation the emitter never does

## Summary

`goc migrate-list-style --help` and `_cmd_migrate_list_style`'s docstring both
list **key order** among the things a canonical re-emit normalises.
`emit_frontmatter` iterates `fm.items()` — the parsed dict, whose insertion
order *is* the authored file's key order — so key order is preserved, never
canonicalised. A card whose only drift is key order is reported as already
canonical, and the per-card changed-part report can never name key order.

## Location

- Subparser help — `goc/engine.py:4137` (the `key order` claim on line 4141)
- `_cmd_migrate_list_style` docstring — `goc/engine.py:7144`
- `emit_frontmatter` — `goc/engine.py:432` (the `for key, value in fm.items()` loop)
- Canonical order source — `_cmd_new`'s `fm = {...}` literal, `goc/engine.py:6207`

## What's broken

The verb's user-facing scope string:

> Re-emit every card into canonical form. Named for the relation-edge list
> (advances/advanced_by/supersedes/superseded_by) block-style migration, but
> normalises everything emit_frontmatter owns — scalar quoting, block scalars,
> **key order**, the blank line before the body. The report names the changed
> part.

and the docstring:

> the predicate is whole-card canonical equality, so scalar quoting,
> block-scalar shape, **key order** and the blank line before the body are
> normalised too.

The emitter it describes has no ordering step at all:

```python
lines = ["---"]
for key, value in fm.items():
    ...
```

`fm` comes from `parse_frontmatter`, which walks the block top-down, so a
Python dict preserves whatever order the author wrote. There is no reference
order in `schema.yaml` either — `required_fields` / `optional_fields` are two
validation lists, and `summary` sits in the optional list while `goc new`
emits it second. The only canonical order that exists is the literal in
`_cmd_new`, and nothing compares a card against it.

The command's own no-op line is the internal contradiction: it enumerates
"relation-edge lists ... plus scalar quoting, block scalars and spacing" and
correctly omits key order, while the help two screens away promises it.

## Empirical evidence

Before the fix, `uv run python .game-of-cards/deck/migrate-list-style-help-promises-key-order-normalisation-the-emitter-never-does/reproduce.py`
exited 1:

```
=== 1. The user-facing strings that promise key-order normalisation ===
  subparser help: ...hing emit_frontmatter owns — scalar quoting, block scalars, key order, the blank line before the bod
  docstring     : ... canonical equality, so scalar quoting, block-scalar shape, key order and the blank line before the

=== 2. emit_frontmatter on a key-reordered card ===
  parsed key order   : ['title', 'status', 'summary', 'stage'] ...
  re-emitted == input: True
  _reemit_changes    : []

=== 3. What `goc migrate-list-style --dry-run` reports for that card ===
  Every card already matches its canonical re-emit — relation-edge lists (advances/advanced_by/supersedes/superseded_by) in block style, plus scalar quoting, block scalars and spacing — nothing to do.

claims key-order normalisation : True
performs key-order normalisation: False
DEFECT PRESENT: True
```

The same result through the installed console script, on a one-card deck whose
only drift is a swapped `summary` / `status` pair:

```
$ goc migrate-list-style --dry-run
Every card already matches its canonical re-emit — ... — nothing to do.
```

After the fix the same script exits 0: sections 2 and 3 are unchanged (the
behaviour was never the defect), and the verdict reads
`claims key-order normalisation : False`.

## Why it matters

The reachability path is a hand-edited card. Frontmatter is edited by hand
routinely — `AGENTS.md` § Card authoring rules tells authors to follow the
emitter's conventions when they do, and every hand edit can reorder keys.
The one verb that exists to sweep such drift back to canonical form advertises
key order as in scope, so a maintainer who reorders a key and then sees
"nothing to do" concludes the deck is canonical when it is not. Worse, the
`--dry-run` report added by
[`migrate-list-style-reports-and-rewrites-far-more-than-list-style`](../migrate-list-style-reports-and-rewrites-far-more-than-list-style/)
exists precisely to name the changed part per card, and key order is the one
listed part it can never name.

This is the third correction to the same scope string. It was first narrowed
to two relation fields, widened to all four by
[`engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields`](../engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields/),
then re-widened to "everything emit_frontmatter owns" by the report-scope card
above — which is where `key order` entered, as a hand-written enumeration of
the emitter's behaviour rather than something derived from it. Kept at three
instances deliberately: the family (a scope string restating emitter behaviour
instead of deriving it) is worth a meta-fix card if a fourth appears, but a
derived string is not obviously reachable for a `--help` line that argparse
renders before any card is read.

## Fix (applied)

Both strings now describe what `emit_frontmatter` actually owns, and each
records the preservation explicitly so the claim is not re-added:

- `goc/engine.py:4137` — the subparser help drops `key order` from the
  normalised set and states `Key order is carried over, not canonicalised.`
- `goc/engine.py:7144` — the docstring drops it too and explains *why* it can
  never be in the set: the emitter walks `fm.items()`, the mapping
  `parse_frontmatter` filled top-down, and no reference order exists to
  normalise toward.

`tests/test_migrate_list_style_key_order_scope.py` pins both halves so they
cannot drift apart again — the behaviour (a key-reordered card round-trips
byte-identically through both the dry-run and the apply path) and the strings
(neither may name key order without denying normalisation). The promise
detector is sentence-scoped rather than substring-scoped, because the corrected
docstring still says the words "key order"; a test case feeds it the original
wording to prove the guard can fail.

Making the emitter *actually* canonicalise key order is the other direction and
is deliberately **not** this card: it would rewrite every card in every
consuming deck on the next emit, concentrate merge-conflict surface on
`README.md` frontmatter against `AGENTS.md` § Parallel-Agent Commit Safety, and
first requires deciding where the canonical order lives (today it is a dict
literal inside `_cmd_new`, not `schema.yaml`). That is a separate, gated card
if anyone wants it.

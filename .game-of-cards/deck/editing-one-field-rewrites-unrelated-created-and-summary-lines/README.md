---
title: editing-one-field-rewrites-unrelated-created-and-summary-lines
summary: "Whole-frontmatter round-trip verbs (`goc wait`, `goc decide`, `goc advance`/`unadvance`) re-emit the entire card through `emit_frontmatter`, which quotes any scalar `_YAML_NEEDS_QUOTE` matches. A legacy bare `summary:` line carrying a colon/comma/backtick is silently flipped bare->quoted even though summary was never the edited field, so the verb's auto-commit bundles an unrelated diff. Value is preserved (no data loss). Sibling of the closed `closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter`, which fixed `closed_at` but did not address this round-trip trap; 3 dogfood cards are currently affected."
status: open
stage: null
contribution: medium
created: "2026-06-06T04:37:25Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero before the chosen fix (drift shown) and continues to exit zero after — but with the synthetic round-trip producing a byte-identical untouched `summary` line and the live-deck survey count for `summary` reporting 0.
  - [ ] TDD: a unittest under `tests/` asserts the chosen invariant — either (path A) no card's `summary` line changes representation under a parse→emit round-trip, or (path B) a round-trip verb leaves every non-target frontmatter line byte-identical.
  - [ ] EMPIRICAL: the chosen mechanism (see `## Decision required`) is recorded in `log.md` with the principle invoked and the closed `closed_at` sibling cited.
  - [ ] MECHANICAL: the 3 affected dogfood cards normalized (path A) or the verbs made line-stable (path B), so `goc wait`/`goc decide`/`goc advance` on any of them produces no `summary` diff; `goc migrate-list-style --dry-run` reports zero `summary`-only rewrites on the dogfood deck.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# Editing one card field rewrites its unrelated bare `created` / `summary` lines

## Location

- Round-trip writers (parse → mutate one field → `emit_frontmatter`):
  `_cmd_wait` (`goc/engine.py:4749`), `_cmd_decide` (`goc/engine.py` `_cmd_decide`),
  `_add_to_list_field` / `_remove_from_list_field` used by `goc advance` /
  `unadvance` / `repair-edges` (`goc/engine.py:4562`), `goc quality-pass`
  summary/DoD rewrites, and `goc migrate-list-style`.
- Emitter quoter: `_YAML_NEEDS_QUOTE = re.compile(r"[:#'\"\\\[\]\{\}\,`@]")`
  (`goc/engine.py:176`) and `_yaml_inline` (`goc/engine.py:244-253`), reached
  for `summary` via the catch-all scalar branch `emit_frontmatter`
  (`goc/engine.py:329`).

## What's broken

`goc wait`, `goc decide`, `goc advance`/`unadvance`, etc. mutate one field by
reading the whole frontmatter, changing one key, and re-emitting the *entire*
mapping through `emit_frontmatter`:

```python
# _cmd_wait (engine.py:4713-4749) — representative of the round-trip verbs
fm, body = parse_frontmatter(text)
...
fm["waiting_until"] = new_until            # the ONLY intended change
(card_dir / "README.md").write_text(emit_frontmatter(fm, body=body))
```

`emit_frontmatter` re-renders every scalar through `_yaml_inline`, which quotes
anything `_YAML_NEEDS_QUOTE` matches:

```python
_YAML_NEEDS_QUOTE = re.compile(r"[:#'\"\\\[\]\{\}\,`@]")
...
if _YAML_NEEDS_QUOTE.search(s) or ...:
    return f'"{escaped}"'
return s
```

A legacy card that stores `summary` *bare* — which the vendored `yaml_lite`
parser reads fine even with embedded `: ` — is therefore re-emitted *quoted*,
on a verb that never touched `summary`:

```yaml
# before `goc wait <title> --until 2027-01-01`
summary: When `workflow.closure_on_integration: true`, `goc done` refuses ...
# after — same value, different representation, unrelated to the overlay edit
summary: "When `workflow.closure_on_integration: true`, `goc done` refuses ..."
```

This is the exact shape of the **closed** sibling
[closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter](../closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter/),
which normalized `closed_at` (251 cards) and aligned the closure writers — but
did not address the *round-trip* trap for other scalar fields. `created` turns
out **not** to be affected in practice (the bare `created` lines in this deck
are all date-only `YYYY-MM-DD` with no quote-trigger; the datetime form is
already quoted), so the live blast radius is `summary` only.

## Empirical evidence

`reproduce.py` (1) does a synthetic round-trip mutating only `waiting_until` and
shows the untouched `summary`/`created` lines flip bare→quoted with the value
preserved, and (2) surveys the live dogfood deck:

```
=== Part 1: synthetic round-trip (mutated only waiting_until) ===
[created]
  BEFORE: created: 2026-06-06T04:37:25Z
  AFTER : created: "2026-06-06T04:37:25Z"
  FLIPPED (spurious diff): True
[summary]
  BEFORE: summary: When `cfg: true`, the verb refuses; commas, colons: all bare here.
  AFTER : summary: "When `cfg: true`, the verb refuses; commas, colons: all bare here."
  FLIPPED (spurious diff): True
  values preserved across round-trip: True

=== Part 2: live dogfood-deck survey ===
  cards with bare quote-trigger created: 0 (each rewritten on the next round-trip verb)
  cards with bare quote-trigger summary: 3 (each rewritten on the next round-trip verb)

DRIFT DEMONSTRATED: True
```

The 3 live-affected cards: `closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded`,
`engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields`,
`repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope`.

## Why it matters

The reachability path is concrete: every round-trip verb above is the shipping
writer for its field, and each ends in `write_text(emit_frontmatter(...))`. When
the verb auto-commits (`_git_auto_commit([card_dir], msg)`), the spurious
`summary` re-quote rides into a commit whose message claims to be about the
overlay/edge change — directly colliding with this repo's **Parallel-Agent
Commit Safety** rule (explicit-pathspec commits must not bundle unrelated
changes) and making the diff misleading to a cold reviewer. `goc
migrate-list-style` would flip all 3 in one sweep under a list-style message.
No data is lost — the harm is representational instability and dishonest diffs.

## Decision required

Two credible fix paths; they are not mutually exclusive but the primary
mechanism is a taste/scope call:

**Path A — normalize to the canonical quoted form (data fix, precedent-aligned).**
Treat emitter-quoted as canonical (the `goc new` emitter already quotes
summaries; bare colon-bearing summaries are fragile YAML only `yaml_lite`
tolerates) and normalize the 3 dogfood cards, exactly as the `closed_at` sibling
migrated its 251. Smallest change; does **not** prevent a future bare field from
re-triggering the trap.

**Path B — make round-trip verbs line-stable (code fix, general).**
Have the single-field verbs edit surgically via `mutate_frontmatter_field`
(already used by the closure verbs precisely "to avoid YAML round-trip")
instead of re-emitting the whole mapping, so *no* untouched line ever changes.
Eliminates the entire class for all current and future fields, at the cost of
touching several verbs.

Sub-questions for whichever path: should `goc validate` gain an advisory that
flags bare scalars the emitter would re-quote (a recurrence guard), and does the
fix ship a consumer-facing normalizer or stay dogfood-only? Pick the mechanism,
then `pull-card` can implement.

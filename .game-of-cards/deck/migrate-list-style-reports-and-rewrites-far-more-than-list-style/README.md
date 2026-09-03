---
title: migrate-list-style-reports-and-rewrites-far-more-than-list-style
summary: "`goc migrate-list-style` chooses which cards to rewrite with `emit_frontmatter(fm, body=body) != original` — a full canonical re-emit — while its subparser help, its docstring and its no-op line all name the four relation-edge list fields as the scope. On this deck the dry run reports 10 cards; all 10 already render `advances`/`advanced_by`/`tags` canonically, and the real diffs are 9 bare-to-quoted `summary` lines plus 1 missing blank line after the frontmatter. So the report is unactionable and the apply path silently performs a whole-card canonicalization under a name that promises only relation-list reformatting."
status: open
stage: null
contribution: medium
created: "2026-09-03T05:32:42Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — on a deck whose relation-edge lists
        are all canonical but which drifts in summary quoting and in the blank
        line after the frontmatter, the dry run names the reason each card was
        picked; the control card with genuine inline-flow `advances` is still
        reported.
  - [ ] MECHANICAL: the `--dry-run` / apply report names, per card, which
        frontmatter keys (and whether the body) the re-emit would change, so a
        reader can tell a relation-list migration from an unrelated
        canonicalization without diffing by hand.
  - [ ] MECHANICAL: the subparser `help=` and the `_cmd_migrate_list_style`
        docstring describe the real predicate — a full canonical frontmatter +
        body re-emit — instead of naming the four relation-edge lists as the
        scope.
  - [ ] MECHANICAL: the no-op line no longer claims only that every card
        `already use[s] block-style for advances/advanced_by/supersedes/superseded_by`
        when what it verified is full canonical equality.
  - [ ] TDD: a regression test in `tests/` pins both directions — a card
        drifting only outside the relation lists is reported WITH its reason,
        and a card drifting only in relation-list rendering is still reported —
        so the fix cannot regress to either "report nothing" or "report
        everything unlabelled".
  - [ ] MECHANICAL: the fix touches neither `emit_frontmatter` nor the set of
        fields it canonicalises. Whether the bare-to-quoted `summary` flip
        should happen at all is owned by the open, decision-gated
        [`editing-one-field-rewrites-unrelated-created-and-summary-lines`](../editing-one-field-rewrites-unrelated-created-and-summary-lines/);
        this card must not pre-empt it, and must not re-emit the 10 live cards.
  - [ ] PROCESS: plugin mirrors re-synced so the four `engine.py` copies stay
        byte-identical; `uv run python -m unittest discover -s tests` and
        `uv run goc validate` green.
---

# `goc migrate-list-style` reports and rewrites far more than list style

## Location

- `goc/engine.py:7099-7127` — `_cmd_migrate_list_style`, the predicate and
  the report.
- `goc/engine.py:4136-4140` — the subparser registration and its `help=`.
- `AGENTS.md` § "Card authoring rules" — the list-field convention the verb
  exists to enforce.

## What's broken

The verb decides what to rewrite by comparing a **full canonical re-emit**
against the file on disk:

```python
rewritten = emit_frontmatter(fm, body=body)
if rewritten != original:
    changed.append(card_dir.name)
```

Every user-facing string around that comparison, however, describes a scope
of exactly four fields. The subparser help and the docstring:

> Re-emit every card to convert relation-edge lists
> (advances/advanced_by/supersedes/superseded_by) to block-style.

and the no-op line:

> All cards already use block-style for
> advances/advanced_by/supersedes/superseded_by — nothing to do.

`emit_frontmatter` canonicalises far more than those four fields: scalar
quoting, block-scalar shape, key ordering, and the blank line that separates
the frontmatter from the body. So the reported set is
"cards not in canonical form", not "cards with list-style drift" — and the
report prints bare card names, giving the reader nothing to distinguish the
two.

Two consequences:

1. **The report is unactionable.** `--dry-run` names N cards under a heading
   that promises relation-list reformatting. A maintainer reading it
   concludes the deck has block-style drift.
2. **The apply path does an unnamed job.** `goc migrate-list-style` with no
   flags rewrites summary quoting and body spacing across the whole deck.
   Combined with the closed
   [`goc-migrate-list-style-leaves-bulk-rewrite-uncommitted`](../goc-migrate-list-style-leaves-bulk-rewrite-uncommitted/)
   behaviour (no auto-commit, working tree left dirty), that is a wide
   uncommitted diff nothing in the invocation announced.

The mismatch got sharper, not softer, when
[`engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields`](../engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields/)
closed: that card made the strings enumerate all four relation fields
confidently, which reads as an exhaustive scope claim over a predicate that
was never scoped to fields at all.

## Empirical evidence

On this repo's live deck, the verb reports 10 cards:

```
$ uv run goc migrate-list-style --dry-run
Would rewrite 10 card(s):
  board-truncates-worker-label-to-eight-characters
  citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks
  claim-drops-existing-worker-where-when-branch-undetectable
  engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields
  goc-tool-files-cards-into-wrong-agents-deck-on-multi-agent-gateways
  marketplace-pin-issue-body-renders-its-instructions-as-a-code-block
  pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries
  symlinked-card-dir-loads-in-queues-but-every-title-verb-rejects-it
  trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir
  waiting-until-with-trailing-newline-passes-wait-then-crashes-reads
Dry run — no changes made.
```

**Not one of the 10 has relation-list drift.** All 10 already carry
`advances: []` / `advanced_by: []` and inline-flow `tags`. The actual diffs
are 9 bare-to-quoted `summary` lines and 1 missing blank line after `---`:

```
#### board-truncates-worker-label-to-eight-characters
-summary: The kanban board hard-caps the worker label to 8 characters (...)
+summary: "The kanban board hard-caps the worker label to 8 characters (...)"

#### marketplace-pin-issue-body-renders-its-instructions-as-a-code-block
 ---
+
 # marketplace-pin-issue-body-renders-its-instructions-as-a-code-block
```

`reproduce.py` isolates this on a synthetic deck:

```
CHECK 1 - deck with NO relation-edge-list drift
  cards on disk ............ ['card-alpha', 'card-beta']
  relation-list drifters ... []
  verb reports to rewrite .. ['card-alpha', 'card-beta']
  verb output:
    | Would rewrite 2 card(s):
    |   card-alpha
    |   card-beta
    | Dry run — no changes made.

CHECK 2 - control: genuine inline-flow relation list
  verb reports to rewrite .. ['card-gamma']

[FAIL] CHECK 1: 2 card(s) reported as list-style migrations while 0 have
relation-list drift, and the report names no other reason
```

## Why it matters

`migrate-list-style` is the deck's only bulk re-emit path, and AGENTS.md
names re-emission as *the* remedy for frontmatter quoting problems:
"Re-emitting the card through any goc verb is the fix." The verb is
therefore load-bearing for more than list style — but an operator cannot
learn that from `--help`, from the dry-run report, or from the no-op line.
The reachability path is ordinary maintenance: a maintainer who reads
AGENTS.md's list-field convention, runs `--dry-run` to check compliance, and
sees 10 cards named has been told something false about their deck; if they
then drop `--dry-run`, they get a deck-wide rewrite of a different kind.

The population is not static: the recently closed
[`goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse`](../goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse/)
widened the emitter's quote trigger to the YAML spec's indicator set, so
every card written before that fix with a now-quotable bare `summary` joined
the reported set without anything about its list style changing.

## Fix (rubric-derived; gate stays `none`)

Keep the predicate, fix what the verb *says* — and make the report name the
reason per card:

1. `goc/engine.py:7100` docstring and `goc/engine.py:4138` `help=`: describe
   the real predicate (re-emit every card into canonical form; relation-edge
   lists are the migration it was introduced for, not the limit of what it
   normalises).
2. `goc/engine.py:7124-7125`: the no-op line should claim canonical form,
   which is what the comparison actually verified.
3. `goc/engine.py:7129-7133`: print, beside each card name, which
   frontmatter keys the re-emit changes and whether the body changes.

Narrowing the predicate to the four relation fields is the rejected
alternative, for two reasons. It would delete the only bulk path to the
remedy AGENTS.md prescribes; and the closed
[`engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields`](../engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields/)
already met this exact shape in this exact verb — strings naming a narrower
scope than the code path — and resolved it by widening the strings to the
code, not by narrowing the code. Whether the bare-to-quoted `summary` flip
should happen at all is a separate, decision-gated question owned by
[`editing-one-field-rewrites-unrelated-created-and-summary-lines`](../editing-one-field-rewrites-unrelated-created-and-summary-lines/);
this card deliberately does not touch `emit_frontmatter` and does not
re-emit the 10 live cards.

Renaming the verb so its name matches its job is a breaking CLI change and
is left out of scope; it needs a maintainer decision, not a fix-through.

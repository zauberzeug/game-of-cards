## 2026-05-29T19:29:58Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Three credible failure modes; the engine has analogues for all three and the
project hasn't settled on a convention for "non-mutating verb call":

1. **`exit 2 + ERROR on stderr`** — matches `_cmd_advance`'s self-edge and
   cycle handling (engine.py:6573, 4393). Strictest: a no-op verb call is a
   user error, surface it.
2. **`exit 0 + WARNING on stderr + no success message`** — least disruptive
   to scripts that call `unadvance` defensively; still distinguishable from
   a real removal. Matches the "advisory" tone of the `STALE_BLOCKED` /
   `ORPHAN_BLOCKED` validators.
3. **`exit 0 + "no edge to remove" success line`** — silent acceptance of
   the idempotent shape. Matches `_remove_from_list_field`'s own no-op
   return (engine.py:6324). Least intrusive but loses information.

Whichever shape the implementer picks should also cover the analogous
`goc wait --clear` on a card without a wait (currently unverified — check
`_cmd_wait` for the same pattern when implementing) so the convention
applies consistently across the verb set.


## 2026-10-22T05:20:22Z: decision recorded

Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: option 1, exit 2 + ERROR on stderr — removing a non-existent edge is refused, symmetric with the advance sibling — The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question. Gate decision → none.


## 2026-10-28T04:34:04Z — Closure

- **What changed**: `goc/engine.py` `_cmd_unadvance` — loads both cards and checks the edge before `_mutate_pair`: either half listed is removed as before (a dangling half included), neither listed is refused with `ERROR: cannot remove <advancer> → <title>: no such edge — …` and exit 2 before any write; when the edge runs the other way the refusal also names `goc unadvance <advancer> --by <title>`. New `_refuse_invalid_input(reason)` is the parent epic's decided one-line shared emission (`ERROR:`, the prefix every mutation verb's precondition refusal already prints, not the query-flag parser's `goc: error:`), and `_cmd_advance`'s self-edge and cycle refusals now route through it with byte-identical output. New `_edge_field_lists(card, field, ref)` reads an edge field the way the graph walkers do (a non-list names nothing). Synced to the three plugin engine mirrors.
- **Shape departs from the fix sketch**: the card preferred a `_mutate_pair` "changed" sentinel because it also covers half-edges, but that writes first and asks afterwards, while the decision requires nothing be written on a refusal. The inline check covers half-edges by accepting either listed half.
- **Re-run contract**: a second `goc unadvance` of the same edge is now refused instead of re-emitting both cards, so `tests/test_verb_rerun_safety.py` declares `unadvance` `REFUSES` (was `RE_EMITS`).
- **Reproducer**: rewritten to the deck's exit-code contract (0 = defect no longer fires, 1 = fires, 2 = harness broken). As filed it exited 0 while the defect fired, the inversion `reproducers-can-exit-zero-while-their-defect-still-fires` describes. It now adds a real-edge control for the DoD's "distinct signal" clause.
- **Verification**: `reproduce.py` exits 0 — the missing edge gets exit 2, `ERROR:` on stderr, no success line and both READMEs untouched, and the real-edge control gets exit 0 and the success line. Against the pre-fix engine it exits 1. `tests/test_mutation_verbs_refuse_invalid_input.py` (6 tests) has 4 failing against the pre-fix engine and all passing now.
- **Checked, left as is**: `goc wait --clear` on a card with no overlay, which the archived deliberation asked the implementer to check. It already prints `<title>: no waiting overlay to clear; nothing to do`, exits 0 and writes nothing. That is an honest no-op, not the misleading success this family refuses.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1395 passed / 0 failed (`uv run python -m unittest discover -s tests`)
- **Records updated**: the parent epic (roster closure, helper and test module named in its dashboard, log entry); `validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments` (its swapped `unadvance` is now refused, not a silent no-op, and the refusal names its corrected command; summary, step 1 and evidence note updated in place, plus a log entry); log entries on `goc-unadvance-with-self-target-leaves-card-in-half-edge-state` (its no-self-edge variant is now refused; the on-disk self-edge variant is unchanged) and `goc-unadvance-rewrites-bare-string-edge-field-as-character-list` (staleness re-check: still live, but an edge whose halves are both bare strings is now refused instead of corrupted). `_edge_field_lists` is a guarded reader, so it adds no unguarded site to `bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`. If that card picks its Option B shared `_field_as_list` helper, the sweep folds this reader in too.

## Closure verification (2026-10-28T04:34:07Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-28 — Closure' present

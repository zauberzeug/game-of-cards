## 2026-05-29T19:42:01Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Three credible options for the failure mode; pick one and apply to BOTH
add and remove directions consistently:

1. **`exit 2 + ERROR`** — strict, mirrors `cannot advance a card with
   itself`. Maximally clear, but breaks any script that retries
   `goc advance` defensively (the second call is currently a quiet
   success; making it a hard failure changes existing behavior).
2. **`exit 0 + WARNING on stderr`** — backward-compatible: the success
   line still fires on stdout, but a `WARNING: edge already exists`
   joins it on stderr. Scripts keep working; humans get an honest
   signal.
3. **`exit 0 + no-op success message`** — replace the misleading
   `advance: ...` line with a distinct `noop: b.advanced_by already
   contains a; nothing to do`. Same exit code as today, distinct
   stdout, easy to grep.

The right choice depends on the resolution of the sibling card; this
card's fix should land second and adopt whichever shape that card picked
so the two verbs stay symmetric.


## 2026-10-22T05:20:21Z: decision recorded

Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: option 1, exit 2 + ERROR — adding an already-existing edge is refused and mutates nothing, symmetric with the unadvance sibling — The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question. Gate decision → none.


## 2026-10-28T04:44:46Z — Closure

- **What changed**: `goc/engine.py` `_cmd_advance` — loads both cards and checks the edge before `_mutate_pair`: with both halves listed (`<title>.advanced_by` names the advancer and `<advancer>.advances` names the title) it refuses through the parent epic's shared `_refuse_invalid_input` with `ERROR: cannot add <advancer> → <title>: the edge already exists — …`, exit 2 before any write; one listed half is completed as before, a new edge is unchanged. The check runs ahead of the cycle guard, so an edge already inside a hand-built cycle is named as existing rather than as a cycle the call would not create; an edge running the other way is still refused by the cycle guard. The `_refuse_invalid_input` docstring now lists the already-present edge among its cases. Synced to the three plugin engine mirrors.
- **Shape**: the inline check the sibling `goc-unadvance-claims-success-when-removing-a-non-existent-edge` used, mirrored (it accepts either listed half; this refuses only when both are listed). The filed sketch, a tri-state `_mutate_pair` result, writes before it can refuse, which the decision rules out.
- **Re-run contract**: a second `goc advance` of the same edge is now refused instead of re-emitting both cards, so `tests/test_verb_rerun_safety.py` declares `advance` `REFUSES` (was `RE_EMITS`).
- **Reproducer**: rewritten to the deck's exit-code contract (0 = defect no longer fires, 1 = fires, 2 = harness broken), driving the real CLI with the first, edge-adding call as the control. As filed it exited 0 while the defect fired, and DoD item 1 had been worded to match (`exits non-zero`) while the body said the DoD flipped it; the item now reads `exits zero`, the same criterion under the corrected contract.
- **Verification**: `reproduce.py` exits 0 — the edge already in place gets exit 2, `ERROR:` on stderr, no success line and both READMEs untouched, while the first call gets exit 0 and the success line. Against the pre-fix engine it exits 1. `AdvanceCliTest` (6 tests) has 3 failing against the pre-fix engine and all passing now; the `advance` row of `test_verb_rerun_safety` fails pre-fix too.
- **Tests refactor**: `tests/test_mutation_verbs_refuse_invalid_input.py` hoists the scratch-deck plumbing into `_ScratchDeckCliTest` with a `_refused(*args, error=…)` assertion for the strict-refuse shape; `UnadvanceCliTest` keeps its five tests unchanged on top of it.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1401 passed / 0 failed (`uv run python -m unittest discover -s tests`)
- **Records updated**: the parent epic (roster closure and a log entry); `validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments` (its swapped second command, `goc advance <child> --by <card>`, names the backwards edge itself and is now refused as already existing; summary, step 2, the evidence note and one sibling-sweep sentence updated in place, plus a log entry; `reproduce.py` still exits 0); `reproducers-can-exit-zero-while-their-defect-still-fires` (log entry: this reproducer and the unadvance sibling's were inverted and fixed on close, and this card's DoD wording had matched the inversion); `sort-tiebreak-double-counts-duplicate-advances-edges` (closed; forward-pointer log entry — repeated `goc advance` never wrote a duplicate entry and now exits 2).
- **Corrected in place**: the body named `goc repair-edges --execute`; the flag is `--apply`. It also said a `goc new --advanced-by` filing could re-assert an already-wired edge; a new card starts with empty edge lists and repeated flags are deduplicated, so at most one half can already be in place.

## Closure verification (2026-10-28T04:44:51Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-28 — Closure' present

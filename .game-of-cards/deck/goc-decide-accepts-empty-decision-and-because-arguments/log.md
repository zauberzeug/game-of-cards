## 2026-05-29T19:53:19Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Two credible failure-mode shapes; pick one:

1. **`exit 2 + ERROR before any mutation`** (strict). Mirrors the
   existing terminal-status guard at `engine.py:4909` and the
   already-`none` gate guard at `engine.py:6866`. The natural choice
   because the resulting body and log entry are not human-readable —
   there is no "lenient success" interpretation that produces a useful
   audit trail. Breaks no tooling that wasn't already producing
   corrupt output.
2. **`exit 0 + WARNING on stderr + still record`** (lenient). Keeps
   the option open for tooling that wants to record a "decided but
   undocumented" state for later annotation. Less appealing — the
   README block and log entry are equally corrupt either way, and a
   "WARNING then succeed" path is the harder-to-discover variant of
   the same broken contract.

Strict (option 1) is the natural sibling of the existing guards in
the same function. Adopt strict unless a concrete tooling use case
appears for the lenient form.


## 2026-10-22T05:20:22Z: decision recorded

Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: option 1, exit 2 + ERROR before any mutation for an empty --decision or --because — The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question. Gate decision → none.


## 2026-10-28T04:56:33Z — Closure

- **What changed**: `goc/engine.py` `_cmd_decide` — right after the `--commit`/`--no-commit` conflict check, before the card is resolved or read, a value that is blank after `.strip()` is refused through the parent epic's shared `_refuse_invalid_input`: `ERROR: <title>: --decision and --because must be non-empty (blank: --decision, --because)`, naming whichever is blank, exit 2, nothing written. Whitespace-only counts as blank, since it renders as nothing in the `## Decision` block and the log entry. The `_refuse_invalid_input` docstring now lists the blank case and says the success line misleads over an empty record as well as over a no-op. Synced to the three plugin engine mirrors.
- **Placement departs from the fix sketch**: the body placed the check after the gate-already-`none` guard; DoD item 3 asked for it before the README is read, which is where it landed. A pure argument check needs no card state (the reason `_cmd_advance` refuses a self-edge before loading either card), so a blank value is refused whatever state the card is in.
- **Docs**: `Skill(decide-card)` "What this skill does to the card" item 4 listed only the gate-already-`none` and missing-title refusals; it now names the blank case and says every refusal exits 2 with nothing written. Template edited, mirrors regenerated, OpenClaw port re-run.
- **Reproducer**: rewritten to the deck's exit-code contract (0 = defect no longer fires, 1 = fires, 2 = harness broken), driving the real CLI over a blank `--decision`, a blank `--because` and both, each on its own parked card so a wrongly lowered gate cannot make the next case look refused, with a filled-in decision as the control. As filed it exited 0 while the defect fired, and on the fixed engine it would have crashed on `out.splitlines()[0]` of an empty stdout instead of printing a verdict. DoD item 1 had been worded to match (`exits non-zero`) while the body said the DoD flipped it; it now reads `exits zero`, the same criterion under the corrected contract.
- **Verification**: `reproduce.py` exits 0: each blank case gets exit 2, `ERROR:` on stderr, no success line and README + log.md untouched, and the control is recorded with exit 0. Against the pre-fix engine (HEAD's `goc/` extracted to a scratch dir) it exits 1 with `DEFECT FIRES` for all three cases. `DecideCliTest` (5 tests) has its 4 refusal tests failing against the pre-fix engine and all passing now.
- **Re-run contract**: unchanged. `tests/test_verb_rerun_safety.py` already declares `decide` `REFUSES` (the second run finds the gate down); its probe passes non-empty values.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1406 passed / 0 failed (`uv run python -m unittest discover -s tests`)
- **Records updated**: the parent epic (roster closure and a log entry); `reproducers-can-exit-zero-while-their-defect-still-fires` (log entry: this reproducer was inverted and was fixed on close).
- **Corrected in place**: "Why it matters" grouped three terminal-status-guard cards with this one as the `accepts unwanted input` family; they belong to `terminal-status-guard-missing-across-mutation-verbs`, which checks card status rather than arguments. The as-filed excerpts are now labeled as such.

## Closure verification (2026-10-28T04:57:15Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-28 — Closure' present

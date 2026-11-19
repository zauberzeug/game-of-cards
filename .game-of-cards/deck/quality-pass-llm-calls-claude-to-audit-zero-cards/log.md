## 2026-11-19T04:54:10Z — Filed as a fix-through

Surfaced while fixing through
`goc-quality-pass-reports-a-clean-deck-in-a-repo-that-has-no-deck`.
Unlike that card, this defect has nothing to do with the missing-deck notice.
It is in the same function the session had loaded, and the fix is one guard
plus its cases in the existing `--llm` test module. That meets the
fix-through bar: gate-free, one site, and close to the loaded context.

- **Dedup**: the deck grepped for `if not live`, `auditing 0`,
  `empty selection`, `zero live` and `no live card`. Every open card on
  `quality-pass --llm` was checked: the DoD-rewrite, null-fix and
  rewrite-count cards, and the active refine-deck reference card, which is
  about documentation. None covers an empty selection.
  `quality-pass-limit-accepts-negative-values-and-audits-wrong-card-subset`
  (done) kept `--limit 0` as a valid value that audits nothing. It did not
  look at whether `claude` is still started.
- **Verdict**: `reproduce.py` exits 1 on `12f1c755`. All four empty
  selections start the fake `claude` once.

## 2026-11-19T04:57:05Z — Closure

- **What changed**: `goc/engine.py` `_cmd_quality_pass` returns before
  building the prompt when the selected sample is empty, and prints
  `Layer-2 (Sonnet pass): no live card selected, so there is nothing to
  audit.` The all-closed path keeps its skip line and nested return. Plugin
  mirrors are re-synced.
- **Verification**: `reproduce.py` exits 0. None of the four empty
  selections starts the fake `claude`, all exit 0, and the one-card control
  still starts it once.
- **Tests**: `tests/test_quality_pass_llm_prompt_delivery.py` gains
  `test_an_empty_selection_never_starts_claude`, whose four subtests and
  control all fail before the fix, and
  `test_an_empty_selection_needs_no_claude_on_path`, which fails before the
  fix with `ERROR: cannot run claude` and exit 1. That module plus
  `tests/test_terminal_status_guard.py`, which holds the all-closed case,
  run 26 tests OK. The full suite ran 1518 tests OK.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a.
- **Other cards**: none describes this defect (dedup in the filing entry).
  The active `refine-deck-reference-calls-the-working-quality-pass-llm-flag-a-stub`
  rewrites the refine-deck reference's `--llm` section and was left alone.
  This fix changes no documented behaviour that the section would have to
  restate.

## Closure verification (2026-11-19T04:57:06Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-11-19T04:57:05Z — Closure' present

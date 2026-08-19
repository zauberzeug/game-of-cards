## 2026-08-19T05:14:37Z — Closure

- **What changed**: `goc/engine.py` — `_cmd_triage`'s constant
  `No parked cards (gate ≠ none).` replaced by `render_empty_triage_line`, which
  names the `status: open` and `gate ≠ none` conjuncts, echoes the `--worker`
  value quoted, and counts the unauthored draft scaffolds it dropped. The
  `--worker` filter now runs before the draft split, so the count is what
  `goc publish` would surface *in this view*. The draft clause moved to the
  shared `_hidden_drafts_clause`, also used by `render_empty_query_line`, whose
  docstring no longer implies triage already carried this contract.
- **Verification**: reproduce.py exits 1 post-fix (5 DEFECT lines and exit 0
  against the pre-fix engine). `tests/test_triage_empty_line.py`: 13 passed;
  against the pre-fix engine the same file gives 8 failures + 2 errors,
  confirming it catches the offender. On this repo's own deck,
  `goc triage --worker nobody` went from `No parked cards (gate ≠ none).` —
  with 184 cards actually parked — to
  `No parked cards (status: open; gate ≠ none; worker: 'nobody').`
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1018 passed / 0 failed / 0 xfailed (full suite, up from 1005).

## Closure verification (2026-08-19T05:14:51Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-08-19 — Closure' present

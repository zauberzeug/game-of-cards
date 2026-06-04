## 2026-06-01T05:03:48Z — Closure

- **What changed**: `goc/engine.py:2885` (subparser `help=`), `goc/engine.py:4541` (`_cmd_repair_edges` docstring), `goc/engine.py:1447` (`find_half_edges` docstring) — all three now name both `advances/advanced_by` and `supersedes/superseded_by` as the verb's scope.
- **Verification**: `tests.test_repair_edges` 5/5 passed (new `test_repair_edges_help_names_both_relation_classes` asserts the parser's `help=` text and both function docstrings mention `supersedes`); full suite 351/351 passed.
- **Audit**: PASS — no principle touched, mechanical fix (doc drift between the implementation's `INVERSE_REL` walk and the user-facing strings describing scope).
- **Project impact**: n/a
- **Tests**: 351 passed / 0 failed / 0 xfailed

## Closure verification (2026-06-01T05:03:58Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-01 — Closure' present

## 2026-09-03T05:46:06Z — Closure

- **What changed**: `goc/engine.py:7146` — `_cmd_migrate_list_style` keeps its
  whole-card canonical re-emit predicate but now reports *what* it would
  rewrite: two new helpers, `_split_card_file` (`:7102`) and
  `_reemit_changes` (`:7128`), diff the original against the canonical
  re-emit per frontmatter key plus the region after the frontmatter, and the
  report prints `<card> — <changed parts>`. The subparser `help=`
  (`:4137`) and the docstring now describe canonical re-emission instead of
  presenting the four relation-edge lists as the scope, and the no-op line
  (`:7180`) claims canonical equality — which is what the comparison
  actually verified — while still naming all four relation fields so the
  contract from `engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields`
  stays pinned.
- **Verification**: on the live deck the dry run went from 10 bare card names
  under a block-style heading to 10 labelled rows — 8 `summary`, 2
  `body spacing`, 0 relation-list drift; `reproduce.py` exits 0 (was 1);
  `tests/test_migrate_list_style_report_scope.py` adds 8 tests.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1084 passed / 0 failed / 0 xfailed
- **Not done deliberately**: the predicate is untouched. Narrowing it to the
  relation lists would delete the only bulk path to the re-emit remedy
  AGENTS.md prescribes, and whether the bare→quoted `summary` flip should
  happen at all belongs to the decision-gated
  `editing-one-field-rewrites-unrelated-created-and-summary-lines`. The 10
  live cards were not re-emitted. Renaming the verb so its name matches its
  job is a breaking CLI change and stays out of scope.

## Closure verification (2026-09-03T05:46:07Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-09-03 — Closure' present

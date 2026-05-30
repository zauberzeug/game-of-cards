## 2026-05-30T08:55Z - zoe-cron

Pulled and implemented the `NotebookEdit` matcher gap. Before the fix, `python3 .game-of-cards/deck/pattern-generalization-mutation-detector-skips-notebookedit-tool-calls/reproduce.py` failed with:

```
tool                 expected   actual     verdict
--------------------------------------------------
Edit                 True       True       ok
Write                True       True       ok
NotebookEdit         True       False      DEFECT
Read                 False      False      ok

FAIL: 1 row(s) diverged from intended behavior. See `CODE_MUTATING_TOOLS` at goc/templates/hooks/pattern_generalization_check.py:22.
```

Changed the Python hook template and OpenClaw TypeScript port to treat `NotebookEdit` as code-mutating, added regression rows for `Edit`, `Write`, `NotebookEdit`, and `Read`, and regenerated plugin/dogfood mirrors with `python3 scripts/sync_plugin_assets.py`. After the fix:

```
tool                 expected   actual     verdict
--------------------------------------------------
Edit                 True       True       ok
Write                True       True       ok
NotebookEdit         True       True       ok
Read                 False      False      ok

PASS: matcher covers all canonical code-mutating tools.
```

Verification:

- `python3 -m unittest tests/test_pattern_generalization_hook.py` -> 14 tests OK
- `python3 scripts/sync_plugin_assets.py --check` -> OK
- `python3 -m pytest tests/test_pattern_generalization_hook.py` could not run because `pytest` is not installed in this runtime; covered with unittest instead.

## 2026-05-30 — closed

Extended the hand-enumerated `CODE_MUTATING_TOOLS` set in
`goc/templates/hooks/pattern_generalization_check.py` from
`frozenset({"Edit", "Write"})` to
`frozenset({"Edit", "Write", "NotebookEdit"})`, and updated the module
docstring's tool enumeration to match. Mirrored the literal in the
hand-ported OpenClaw TS port at `openclaw-plugin/index.ts:292`.

`scripts/sync_plugin_assets.py` mirrored the Python change into
`.claude/hooks/`, `claude-plugin/hooks/`,
`claude-plugin/goc/templates/hooks/`, `codex-plugin/hooks/`, and
`codex-plugin/goc/templates/hooks/`. The OpenClaw TS port is not
auto-synced — edited directly.

Before (reproduce.py):

```
tool                 expected   actual     verdict
--------------------------------------------------
Edit                 True       True       ok
Write                True       True       ok
NotebookEdit         True       False      DEFECT
Read                 False      False      ok

FAIL: 1 row(s) diverged from intended behavior. See `CODE_MUTATING_TOOLS` at
goc/templates/hooks/pattern_generalization_check.py:22.
```

After:

```
tool                 expected   actual     verdict
--------------------------------------------------
Edit                 True       True       ok
Write                True       True       ok
NotebookEdit         True       True       ok
Read                 False      False      ok

PASS: matcher covers all canonical code-mutating tools.
```

Regression coverage: `tests/test_pattern_generalization_hook.py`
gains a `CodeMutatingToolSetTest` class that pins one row per
canonical mutator (`Edit`, `Write`, `NotebookEdit`) plus the
read-only baseline (`Read`).

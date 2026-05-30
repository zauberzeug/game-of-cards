## 2026-05-30 — closed

Replaced the substring-containment check
(`any(tok in cmd for tok in BASH_COMMIT_TOKENS)`) in
`goc/templates/hooks/pattern_generalization_check.py` with an anchored
regex:

```python
_BASH_COMMIT_RE = re.compile(
    r"\bgit\s+commit\b|\bgit\s+add\s+(?:-[A-Za-z]|\.)"
)
```

The same defect lived in `openclaw-plugin/index.ts` where the regex
`/\bgit\s+add\s+[-.]/` matched `--` via the `-` in the char class.
Tightened to `/\bgit\s+add\s+(?:-[A-Za-z]|\.)/` so a single dash must
be followed by a letter, not another dash.

`scripts/sync_plugin_assets.py` mirrored the Python change into
`.claude/hooks/`, `claude-plugin/hooks/`,
`claude-plugin/goc/templates/hooks/`, `codex-plugin/hooks/`, and
`codex-plugin/goc/templates/hooks/`. The OpenClaw TS port is not
auto-synced — edited directly.

Before (reproduce.py):

```
'git commit -- foo.py'         True       True       ok
'git add -A'                   True       True       ok
'git add foo.py'               False      False      ok
'git add -- foo.py'            False      True       DEFECT
FAIL: 1 row(s) diverged from intended behavior.
```

After:

```
'git commit -- foo.py'         True       True       ok
'git add -A'                   True       True       ok
'git add foo.py'               False      False      ok
'git add -- foo.py'            False      False      ok
PASS: matcher rejects pathspec-separator staging.
```

Regression coverage: `tests/test_pattern_generalization_hook.py` pins
the four rows above plus `git commit -m`, `git add -p`, `git add -u`,
`git add .`, `git status`, and `git add -- foo.py bar.py`.

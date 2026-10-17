## 2026-10-17T05:07:27Z — Closure

- **What changed**: `goc/engine.py:5942` — the `subprocess.run` call in
  `_run_automated_check` decodes check output with
  `errors="backslashreplace"`. `goc/engine.py:5951-5958` — a new
  `except OSError` branch after the `FileNotFoundError` one returns
  `(False, "cannot run <program>: <reason>")`, with the program taken from
  `exc.filename`, so it never indexes `cmd`. `tests/test_attest_automated_check_cannot_run.py`
  is new (5 tests on real commands: no executable bit, no shebang,
  undecodable stdout at exit 0 and stderr at exit 1, plus the
  missing-command control). `tests/test_attest_automated_timeout.py`'s
  exact-call pin gains the new keyword. The plugin engine mirrors are
  regenerated.
- **Verification**: reproduce.py exit 1 → 0. All 3 crash cases now exit 2
  with a `[ ] <check> — cannot run …` / `exit 1: caf\xe9 \xff failed` row
  and a closure-verification block, with no traceback. Run against the
  pre-fix engine (a `git archive` of the claim commit), the new test file
  fails with 6 errors and passes after the fix. The missing-command control
  passes on both sides. `sync_plugin_assets.py --check`,
  `port_skills_to_openclaw.py --check`, `goc validate` and the
  card-language and strict-YAML guards are green.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1336 passed / 0 failed / 0 xfailed
- **Bundled with**: none
- **Related**: the two `cmd` *shape* crashes found on the way — a
  non-string element raises `TypeError`, an empty list `IndexError` — are
  recorded as supporting evidence on
  `attest-cmd-as-string-fails-with-misleading-single-character-not-found-error`.
  That card keeps the shape decision and the `command not found: {cmd[0]}`
  message.

## Closure verification (2026-10-17T05:07:31Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-17 — Closure' present

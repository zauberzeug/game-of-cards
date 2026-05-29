## 2026-05-29T07:52:00Z — Closure

- **What changed**: `goc/cli.py:26` — `main()` now restores `signal.SIG_DFL` for `SIGPIPE` before argv dispatch (guarded for Windows / non-main-thread import via `try/except (AttributeError, ValueError)`).
- **Verification**: `tests/test_sigpipe_handler.py` runs `python -m goc.cli --done` through a closed pipe and asserts stderr contains neither `BrokenPipeError` nor `Exception ignored`; `reproduce.py` now exits 0; `uv run goc --done | head -3` produces an empty stderr.
- **Audit**: PASS — no project rubric configured (`.game-of-cards/hooks/finish-card.md` empty); mechanical fix.
- **Project impact**: n/a.
- **Tests**: 206 passed / 0 failed (full suite); the new regression test is `tests/test_sigpipe_handler.py`.
- **Bundled with**: —

## Closure verification (2026-05-29T07:52:11Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

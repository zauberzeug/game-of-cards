## 2026-08-19T04:58:06Z — Closure

- **What changed**: `goc/engine.py:5549` — new `_prompt_line` EOF-safe reader; the four
  `input()` calls in `_prompt_yes_no` / `_prompt_manual` / `_prompt_agent` now route
  through it, so EOF yields the declined outcome `--non-interactive` already defines
  instead of an `EOFError` escaping a check loop that catches only `KeyboardInterrupt`.
- **Verification**: reproduce.py exits 0 (was 1 with `EOFError`); `goc attest` on a
  `manual` check with stdin at EOF now prints `[ ] docs-updated — (declined)` and exits 2
  rather than a traceback. Piped-answer and `--non-interactive` paths byte-identical.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1005 passed / 0 failed (`uv run python -m unittest discover -s tests`),
  including 6 new in `tests/test_attest_prompt_eof.py`. The new tests were run against
  the pre-fix engine and produced 3 errors + 1 failure, confirming they catch the offender
  rather than merely passing.

## Closure verification (2026-08-19T04:58:09Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-19 — Closure' present

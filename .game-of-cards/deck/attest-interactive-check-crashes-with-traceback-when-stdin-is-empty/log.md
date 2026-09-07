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

## 2026-08-20: forward pointer — the cited three-site convention was half-implemented

This card's body argued from `confirm`, `install._confirm` and the
briefing-target picker as the settled standard for "prompt that may run
without a terminal". A later audit found that all three guarded EOF on their
non-TTY `readline()` branch only — a call that returns `""` at EOF and cannot
raise `EOFError` — leaving the TTY `input()` branch, the one a human reaches
with Ctrl-D, bare. So the convention cited here existed for piped callers and
not for terminal ones, and `_prompt_line` (delivered by this card, with no
`isatty()` branch at all) was the more correct pattern of the two.

Filed and fixed as
`ctrl-d-at-a-goc-confirmation-prompt-crashes-with-a-traceback`, which routes
all three older sites through an EOF-safe reader and widens this card's AST
guard from the four attest helpers to every `input()` call in `goc/engine.py`
and `goc/install.py`. The claims in the body above are corrected in place; the
fix this card delivered is unaffected.

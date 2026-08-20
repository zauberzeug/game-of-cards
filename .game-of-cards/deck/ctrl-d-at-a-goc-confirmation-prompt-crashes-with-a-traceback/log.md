## 2026-08-20T04:50:31Z — Closure

- **What changed**: `goc/engine.py:3795` (`confirm`), `goc/install.py:1447`
  (new `_prompt_line` + `_confirm`), `goc/install.py:1668` (briefing-target
  picker) — the TTY `input()` read at all three prompt sites now goes through
  an EOF-safe reader, so Ctrl-D takes the prompt's `default` instead of
  raising `EOFError` out of the verb.
- **Verification**: `reproduce.py` exits 0 — `engine.confirm` and
  `install._confirm` both return `False` at EOF, and `goc migrate` under a
  pty with Ctrl-D exits 1 with `EOFError in stderr: False` and the legacy tree
  intact (was a traceback). The new `tests/test_confirm_prompt_eof.py`
  produces 4 errors + 2 failures against the pre-fix engine (`git archive HEAD`
  into a scratch tree), confirming it catches the offender rather than merely
  passing.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is empty); mechanical fix. No principle touched: an empty answer already
  meant "take the default" at all three sites, so folding EOF into it adds no
  semantics — it removes a crash from a path that already had a defined
  outcome. The `isatty()` branch is preserved because it selects prompt echo,
  and a regression test pins that a piped caller still sees no prompt on stdout.
- **Project impact**: n/a
- **Tests**: 1028 passed / 0 failed (was 1018 — 10 new), `goc validate` clean
  over 731 cards, `sync_plugin_assets.py --check` and
  `port_skills_to_openclaw.py --check` both OK after re-syncing the four
  engine mirrors.
- **Also amended**: `attest-interactive-check-crashes-with-traceback-when-stdin-is-empty`
  — its body claimed these three sites "already guard exactly this case"; the
  claim is corrected in place and a forward pointer appended to its log.md.

## Closure verification (2026-08-20T04:50:31Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-08-20 — Closure' present

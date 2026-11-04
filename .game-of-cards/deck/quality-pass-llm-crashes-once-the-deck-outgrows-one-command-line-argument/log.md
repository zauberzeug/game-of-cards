## 2026-11-04T04:29:24Z — Closure

- **What changed**: `goc/engine.py:5190-5191`: `_run_sonnet_quality_pass`
  runs `claude --model sonnet -p --output-format json` and writes the
  prompt to its stdin (`input=prompt`, `encoding="utf-8"`), so no argv
  element carries the cards. The `shutil.which` pre-check is gone, and
  the launch itself decides. `goc/engine.py:5424-5448`: the call site catches
  `FileNotFoundError` (`ERROR: cannot run claude: the `claude` CLI is not
  on PATH; …`), then any other `OSError` (`ERROR: cannot run claude:
  <strerror>`, the `_run_automated_check` shape). It prints the error
  envelope as itself, and keeps "could not parse Sonnet response" for
  replies that do not parse. `goc/engine.py:4528-4530`: the `--llm` help
  drops "Sonnet-batched" and says the pass is one `claude -p` call over each
  selected live card's title, summary and DoD.
  `tests/test_terminal_status_guard.py`: the fake `claude` records argv,
  then stdin, into `claude-input.txt`, and `_goc` closes stdin
  (`subprocess.DEVNULL`) so the fake's `cat` cannot block. New
  `tests/test_quality_pass_llm_prompt_delivery.py`. Engine mirrors synced.
- **Verification**: `reproduce.py` went from exit 1 before the fix (100-card
  deck: 0/100 titles delivered, `OSError: [Errno 7] Argument list too
  long`) to exit 0 after it (100/100 in one call, no traceback). This repo's
  own deck now delivers 183 titles in one call. The new test module has 7
  tests. On the pre-fix engine 6 fail, with 8 reports counting subtests (4
  failures, 4 errors). The 100-card run exits 1 on `E2BIG`. The help says
  "batched". A missing `claude` (real CLI, empty PATH) and an error envelope
  both read "could not parse". Each injected launch error (`E2BIG`,
  `EACCES`, `ENOEXEC`, `ENOENT`) escapes as a traceback. The 7th test, an
  unparseable reply still reported as one, held before and still holds. The argv-only fake, run unchanged against the fixed engine,
  fails `test_quality_pass_llm_keeps_closed_cards_out_of_the_llm_sample`
  (`'live-card' not found in '--model\nsonnet\n-p\n--output-format\njson\n'`),
  so the fake update is load-bearing. The stdin contract was checked
  locally with no API call. `claude -p --output-format json < /dev/null` on
  Claude Code 2.1.318 answers `Error: Input must be provided either through
  stdin or as a prompt argument when using --print`.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: `goc quality-pass --llm` runs on a deck of any size
  (this repo's 183 open cards included) instead of crashing past about 80
  cards, and an unattended caller gets one `ERROR:` line naming the launch
  failure instead of a traceback. Not done: batching. One call still carries
  every selected card, and whether one response holds 183 verdicts is
  unmeasured. The new test ties "one call" to the help text.
- **Tests**: 1469 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`). `uv run goc validate`
  has 0 errors, `sync_plugin_assets.py --check` is green, and the
  card-language and strict-YAML guards are clean.

## Closure verification (2026-11-04T04:29:51Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-11-04T04:29:24Z — Closure' present

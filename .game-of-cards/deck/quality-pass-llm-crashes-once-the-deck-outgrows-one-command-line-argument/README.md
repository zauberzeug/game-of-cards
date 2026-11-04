---
title: quality-pass-llm-crashes-once-the-deck-outgrows-one-command-line-argument
summary: "goc quality-pass --llm handed every selected card's title, summary and DoD to claude -p as one command-line argument, and Linux refuses a single argument over 128 KiB, so on a deck of more than about 80 open cards the pass died with an uncaught OSError (Argument list too long) traceback before Claude started; this repo's own 183 open cards render a 293,758-byte prompt. Fixed by writing the prompt to claude's stdin, which has no per-argument cap, so every selected card now reaches it. A failed launch ends in one ERROR line, a missing claude is no longer reported as an unparseable response, and the --llm help no longer promises a batched pass."
status: done
stage: null
contribution: medium
created: "2026-11-02T00:54:14Z"
closed_at: "2026-11-04T04:29:53Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits 0 — on its 100-card synthetic deck (171,446 bytes of card JSON) `goc quality-pass --llm --dry-run` exits 0, prints no traceback, and all 100 titles reach `claude`.
  - [x] TDD: a regression test in `tests/` runs `goc quality-pass --llm` through a fake `claude` over a deck whose prompt exceeds 131,072 bytes and asserts that every selected card reaches it; the test fails on the pre-fix engine.
  - [x] TDD: an `OSError` raised while starting `claude` ends the run with one `ERROR:` line naming the launch failure and exit 1, no traceback; a missing `claude` is no longer reported as "could not parse Sonnet response".
  - [x] MECHANICAL: the `--llm` help (`goc/engine.py:4529`) matches what the pass does — no "batched" claim unless it batches — and the fake `claude` in `tests/test_terminal_status_guard.py` captures the prompt wherever the fix sends it.
  - [x] PROCESS: `python scripts/sync_plugin_assets.py --check` clean; `uv run python -m unittest discover -s tests` green; `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc quality-pass --llm` crashed once the deck outgrew one command-line argument

## Location

- `goc/engine.py:5190-5191` — `_run_sonnet_quality_pass` now runs
  `claude --model sonnet -p --output-format json` and writes the prompt to
  its stdin:

  ```python
  cmd = ["claude", "--model", "sonnet", "-p", "--output-format", "json"]
  result = subprocess.run(cmd, input=prompt, capture_output=True, encoding="utf-8", check=True)
  ```

  Before the fix the prompt was one argv element:
  `cmd = ["claude", "--model", "sonnet", "-p", prompt, "--output-format", "json"]`.
- `goc/engine.py:5154-5164` — `_build_quality_prompt` renders the title,
  summary and `definition_of_done` of every card in the sample into that
  string (`json.dumps(slim, indent=2)` inside a 2,374-byte instruction
  template).
- `goc/engine.py:5421` — `sample = live if limit is None else live[:limit]`:
  without `--limit`, every selected live card goes into the one prompt.
- `goc/engine.py:5424-5448` — the call site. It used to catch only
  `subprocess.CalledProcessError` and
  `(ValueError, json.JSONDecodeError, RuntimeError)`, so a failure to start
  the process, an `OSError`, escaped both clauses.
- `goc/engine.py:4528-4530` — the `--llm` help, which used to read "Also
  run a Sonnet-batched summary+DoD audit (closed cards are skipped)."
- `goc/engine.py:1222` — `load_all_cards` walks `sorted(DECK_DIR.iterdir())`,
  so `--limit N` always keeps the alphabetically first N cards.

## What was broken

Linux caps every single argv string at `MAX_ARG_STRLEN`, 32 pages (131,072
bytes on 4 KiB pages), however large the total `ARG_MAX` is (4 MiB on the
host this was measured on). `execve` refuses a longer argument with `E2BIG`,
which `subprocess` raises from `Popen` as
`OSError: [Errno 7] Argument list too long: 'claude'`.

The prompt grows with every selected card. On this repo's deck that is about
1.6 KB per card (mean 1,592 bytes, median 1,500) on top of the template. So
a default run (`--status open`) crossed the limit at about 80 cards. Beyond
that, `goc quality-pass --llm` could never start Claude. The `OSError`
escaped both `except` clauses, so the run ended in a raw traceback after
Layer 1 had printed, not in the one-line `ERROR:` the two caught branches
print.

The help called the pass "Sonnet-batched", but it sent exactly one unbounded
batch. The only lever was `--limit`, which is documented for testing and
sampling. `_cmd_quality_pass` cuts the sample from an alphabetical list and
reads no offset, title filter or tag filter, so every capped run re-audited
the same alphabetical prefix. Cards past the cut-off never reached the model.

The same `except` block also mislabeled a launch failure it did catch.
`_run_sonnet_quality_pass` raised
`RuntimeError("`claude` CLI not on PATH; …")` when the CLI was missing, and
the handler printed it as
``ERROR: could not parse Sonnet response: `claude` CLI not on PATH; cannot run --llm pass.``.
No response existed to parse. An error envelope from `claude` (for example
"not logged in") went out under the same "could not parse" label.

## Empirical evidence

`uv run python .game-of-cards/deck/quality-pass-llm-crashes-once-the-deck-outgrows-one-command-line-argument/reproduce.py`
on `main` before the fix (2026-11-02):

```
Linux per-argument limit (MAX_ARG_STRLEN): 131072 bytes
[control]  5 cards, card JSON 8542 bytes: exit 0, claude calls 1, titles delivered 5/5
[verdict]  100 cards, card JSON 171446 bytes: exit 1, claude calls 0, titles delivered 0/100, traceback yes
           stderr tail: OSError: [Errno 7] Argument list too long: 'claude'
[info]     copy of this repo's deck: exit 1, claude calls 0, titles delivered 0, traceback yes
           stderr tail: OSError: [Errno 7] Argument list too long: 'claude'

DEFECT FIRES: `goc quality-pass --llm` cannot audit a deck whose prompt exceeds one command-line argument.
```

After the fix (2026-11-04):

```
Linux per-argument limit (MAX_ARG_STRLEN): 131072 bytes
[control]  5 cards, card JSON 8542 bytes: exit 0, claude calls 1, titles delivered 5/5
[verdict]  100 cards, card JSON 171446 bytes: exit 0, claude calls 1, titles delivered 100/100, traceback no
           stderr tail: (empty)
[info]     copy of this repo's deck: exit 0, claude calls 1, titles delivered 183, traceback no
           stderr tail: (empty)

OK: every card reached claude and the run exited 0.
```

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = harness or
precondition broken (a non-Linux host, a failed control run, or a crash in
the script itself).

The harness drives only the CLI, and a fake `claude` is the only entry on
PATH. CPython's exec loop tries every PATH entry in turn, so a fake that
failed to start must never hand the deck to a real `claude`. Two cross-checks
were run against the same script when it was written:

- An engine copy patched to send the prompt on stdin exits 0, with 100/100
  titles delivered.
- With the fake made non-executable, the script exits 2.

Measured directly on this repo's deck before the fix (2026-11-02,
`_build_quality_prompt` over the cards each invocation selects):

| invocation | cards sent | prompt bytes | vs. 131,072 |
|---|---|---|---|
| `goc quality-pass --llm` (default `--status open`, one draft included) | 183 | 293,758 | 2.24×, crashed |
| `... --llm --limit 78` (largest prefix that fits) | 78 | under the limit | ran |
| `... --llm --limit 79` | 79 | over the limit | crashed |

So 105 of the 183 open cards could not reach the pass through any
invocation.

## Why it matters

- **Reachability.** No crafted input was needed. On Linux, the plain
  invocation `goc quality-pass --llm` failed for any deck past about 80 open
  cards. That is the command `Skill(refine-deck)`'s routing table names for
  the flag, and this repo's deck is more than twice past the threshold.
  Nothing in the autonomous workflows passes `--llm` today: refine-deck's
  flow runs `goc quality-pass --status all`, regex only. So the crash met
  whoever opted in, on the first try.
- **An unattended caller got a crash, not a diagnosis.** The traceback named
  neither the deck size nor `--limit`.
- **The workaround never covered the whole deck.** `--limit 78` kept the run
  alive by auditing the same 78 cards every time.
- **A doc fix is about to call the flag working.** The active card
  [refine-deck-reference-calls-the-working-quality-pass-llm-flag-a-stub](../refine-deck-reference-calls-the-working-quality-pass-llm-flag-a-stub/)
  rewrites `Skill(refine-deck)`'s reference section to explain what `--llm`
  sends and to name `--dry-run`, `--yes` and `--limit`. Before this fix the
  flag did not run at all on this repo's deck without `--limit`.

## Fix

1. **The prompt travels on stdin.** `_run_sonnet_quality_pass` runs
   `claude --model sonnet -p --output-format json` with
   `subprocess.run(cmd, input=prompt, ...)`. Print mode reads its prompt
   from stdin when none is given on the command line; with neither, Claude
   Code 2.1.318 answers
   `Error: Input must be provided either through stdin or as a prompt argument when using --print`.
   A pipe has no per-argument cap, and it keeps the deck's text out of the
   process table. The pipe is UTF-8 both ways (`encoding="utf-8"`, not
   `text=True`): the locale's codec may lack the template's `≥` and `σ`,
   which argv never had to encode through it.
2. **A failed launch is one `ERROR:` line and exit 1.** The call site catches
   `FileNotFoundError` first: `ERROR: cannot run claude: the `claude` CLI is
   not on PATH; --llm needs Claude Code installed and logged in.` Any other
   `OSError` prints `ERROR: cannot run claude: <strerror>`, the shape of
   `_run_automated_check`'s handler. The `shutil.which` pre-check is gone,
   so the launch itself decides: a `claude` without the executable bit
   now reports `Permission denied` rather than "not on PATH". An error
   envelope prints as itself (`ERROR: claude CLI reported error: '…'`), and
   "could not parse Sonnet response" is left to replies that do not parse.
3. **The fake `claude` in `tests/test_terminal_status_guard.py`** records
   argv and then stdin into one `claude-input.txt`, and that class's `_goc`
   passes `stdin=subprocess.DEVNULL` so the fake's `cat` never waits on the
   test runner's stdin. Unchanged, the argv-only fake fails
   `test_quality_pass_llm_keeps_closed_cards_out_of_the_llm_sample` on the
   fixed engine (`'live-card' not found in '--model\nsonnet\n-p\n--output-format\njson\n'`).
4. **The `--llm` help says what the pass does**: "Also audit each selected
   live card's title, summary and DoD with Sonnet, all in one `claude -p`
   call (closed cards are skipped)."

`tests/test_quality_pass_llm_prompt_delivery.py` pins items 1, 2 and 4. It
covers a 100-card deck that clears the per-argument limit, each launch
`OSError`, a missing `claude` through the real CLI, the error envelope, and
an unparseable reply. It also checks that the help names one call while the
pass makes exactly one.

**Not done: batching.** One call still carries every selected card and asks
for one verdict record per card in a single response. Whether one response
holds 183 verdicts is unmeasured, since no API call was made. If a real run
truncates, bound each call by bytes and concatenate the verdict lists. The
test above ties "one call" to the help text, so that change must update both.
`--limit` still takes the alphabetical prefix, but a large deck no longer
needs it.

---
title: quality-pass-llm-crashes-once-the-deck-outgrows-one-command-line-argument
summary: "goc quality-pass --llm hands every selected card's title, summary and DoD to claude -p as one command-line argument, and Linux refuses a single argument over 128 KiB, so on a deck of more than about 80 open cards the pass dies with an uncaught OSError (Argument list too long) traceback before Claude starts. This repo's own 183 open cards render a 293,758-byte prompt, and the only workaround, --limit N, always takes the alphabetically first N cards, so most of a large deck can never be audited."
status: active
stage: null
contribution: medium
created: "2026-11-02T00:54:14Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits 0 — on its 100-card synthetic deck (171,446 bytes of card JSON) `goc quality-pass --llm --dry-run` exits 0, prints no traceback, and all 100 titles reach `claude`.
  - [ ] TDD: a regression test in `tests/` runs `goc quality-pass --llm` through a fake `claude` over a deck whose prompt exceeds 131,072 bytes and asserts that every selected card reaches it; the test fails on the pre-fix engine.
  - [ ] TDD: an `OSError` raised while starting `claude` ends the run with one `ERROR:` line naming the launch failure and exit 1, no traceback; a missing `claude` is no longer reported as "could not parse Sonnet response".
  - [ ] MECHANICAL: the `--llm` help (`goc/engine.py:4529`) matches what the pass does — no "batched" claim unless it batches — and the fake `claude` in `tests/test_terminal_status_guard.py` captures the prompt wherever the fix sends it.
  - [ ] PROCESS: `python scripts/sync_plugin_assets.py --check` clean; `uv run python -m unittest discover -s tests` green; `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc quality-pass --llm` crashes once the deck outgrows one command-line argument

## Location

- `goc/engine.py:5182-5183` — `_run_sonnet_quality_pass` passes the whole
  prompt as a single argv element:

  ```python
  cmd = ["claude", "--model", "sonnet", "-p", prompt, "--output-format", "json"]
  result = subprocess.run(cmd, capture_output=True, text=True, check=True)
  ```

- `goc/engine.py:5153-5163` — `_build_quality_prompt` renders the title,
  summary and `definition_of_done` of every card in the sample into that
  string (`json.dumps(slim, indent=2)` inside a 2,374-byte instruction
  template).
- `goc/engine.py:5413` — `sample = live if limit is None else live[:limit]`:
  without `--limit`, every selected live card goes into the one prompt.
- `goc/engine.py:5416-5423` — the call site catches
  `subprocess.CalledProcessError` and
  `(ValueError, json.JSONDecodeError, RuntimeError)`. A failure to start the
  process is an `OSError`, which neither clause catches.
- `goc/engine.py:4529` and `:4533` — the contract: `--llm` will "Also run a
  Sonnet-batched summary+DoD audit (closed cards are skipped)."; `--limit` is
  "With --llm: cap card count (testing/sampling)."
- `goc/engine.py:1224` — `load_all_cards` walks `sorted(DECK_DIR.iterdir())`,
  so `--limit N` always keeps the alphabetically first N cards.

## What's broken

Linux caps every single argv string at `MAX_ARG_STRLEN`, 32 pages (131,072
bytes on 4 KiB pages), however large the total `ARG_MAX` is (4 MiB on the
host this was measured on). `execve` refuses a longer argument with `E2BIG`,
which `subprocess` raises from `Popen` as
`OSError: [Errno 7] Argument list too long: 'claude'`.

The prompt grows with every selected card. On this repo's deck that is about
1.6 KB per card (mean 1,592 bytes, median 1,500) on top of the template. So
a default run (`--status open`) crosses the limit at about 80 cards. Beyond
that, `goc quality-pass --llm` can never start Claude. The `OSError` escapes
both `except` clauses, so the run ends in a raw traceback after Layer 1 has
printed, not in the one-line `ERROR:` the two caught branches print.

The help calls the pass "Sonnet-batched", but it sends exactly one unbounded
batch. The only lever is `--limit`, which is documented for testing and
sampling. `_cmd_quality_pass` cuts the sample from an alphabetical list and
reads no offset, title filter or tag filter, so every capped run re-audits
the same alphabetical prefix. Cards past the cut-off never reach the model.

The same `except` block also mislabels a launch failure it does catch.
`_run_sonnet_quality_pass` raises
`RuntimeError("`claude` CLI not on PATH; …")` when the CLI is missing, and
the handler prints it as
``ERROR: could not parse Sonnet response: `claude` CLI not on PATH; cannot run --llm pass.``.
No response existed to parse.

## Empirical evidence

`uv run python .game-of-cards/deck/quality-pass-llm-crashes-once-the-deck-outgrows-one-command-line-argument/reproduce.py`
on `main` (2026-11-02):

```
Linux per-argument limit (MAX_ARG_STRLEN): 131072 bytes
[control]  5 cards, card JSON 8542 bytes: exit 0, claude calls 1, titles delivered 5/5
[verdict]  100 cards, card JSON 171446 bytes: exit 1, claude calls 0, titles delivered 0/100, traceback yes
           stderr tail: OSError: [Errno 7] Argument list too long: 'claude'
[info]     copy of this repo's deck: exit 1, claude calls 0, titles delivered 0, traceback yes
           stderr tail: OSError: [Errno 7] Argument list too long: 'claude'

DEFECT FIRES: `goc quality-pass --llm` cannot audit a deck whose prompt exceeds one command-line argument.
```

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = harness or
precondition broken (a non-Linux host, a failed control run, or a crash in
the script itself).

The harness drives only the CLI, and a fake `claude` is the only entry on
PATH. CPython's exec loop tries every PATH entry in turn, so a fake that
failed to start must never hand the deck to a real `claude`. Two cross-checks
were run against the same script:

- An engine copy patched to send the prompt on stdin exits 0, with 100/100
  titles delivered.
- With the fake made non-executable, the script exits 2.

Measured directly on this repo's deck (2026-11-02, `_build_quality_prompt`
over the cards each invocation selects):

| invocation | cards sent | prompt bytes | vs. 131,072 |
|---|---|---|---|
| `goc quality-pass --llm` (default `--status open`, one draft included) | 183 | 293,758 | 2.24×, crashes |
| `... --llm --limit 78` (largest prefix that fits) | 78 | under the limit | runs |
| `... --llm --limit 79` | 79 | over the limit | crashes |

So 105 of the 183 open cards cannot reach the pass through any invocation.

## Why it matters

- **Reachability.** No crafted input is needed. On Linux, the plain
  invocation `goc quality-pass --llm` fails for any deck past about 80 open
  cards. That is the command `Skill(refine-deck)`'s routing table names for
  the flag, and this repo's deck is more than twice past the threshold.
  Nothing in the autonomous workflows passes `--llm` today: refine-deck's
  flow runs `goc quality-pass --status all`, regex only. So the crash meets
  whoever opts in, on the first try.
- **An unattended caller gets a crash, not a diagnosis.** The traceback names
  neither the deck size nor `--limit`.
- **The workaround never covers the whole deck.** `--limit 78` keeps the run
  alive by auditing the same 78 cards every time.
- **A doc fix is about to call the flag working.** The active card
  [refine-deck-reference-calls-the-working-quality-pass-llm-flag-a-stub](../refine-deck-reference-calls-the-working-quality-pass-llm-flag-a-stub/)
  rewrites `Skill(refine-deck)`'s reference section to explain what `--llm`
  sends and to name `--dry-run`, `--yes` and `--limit`. On this repo's deck
  the flag does not run at all without `--limit`.

## Fix (not applied)

1. **Send the prompt on stdin.** Use
   `cmd = ["claude", "--model", "sonnet", "-p", "--output-format", "json"]`
   with `subprocess.run(cmd, input=prompt, ...)`. Print mode takes stdin:
   Claude Code 2.1.316, given neither stdin nor a prompt, answers
   `Error: Input must be provided either through stdin or as a prompt argument when using --print`.
   A pipe has no per-argument cap, and it also keeps the deck's text out of
   the process table.
2. **Catch `OSError` at the call site** (`goc/engine.py:5416-5423`). Report
   it as one `ERROR:` line naming the launch failure, then exit 1. Give the
   missing-CLI `RuntimeError` its own wording. The shape to copy already
   exists in the engine: `_run_automated_check` (`goc/engine.py:6372-6379`)
   catches `OSError` and reports `cannot run {program}: {exc.strerror or exc}`,
   using `exc.filename`. That handler was added by the closed
   [attest-automated-check-crashes-with-traceback-when-its-command-cannot-run-or-prints-undecodable-bytes](../attest-automated-check-crashes-with-traceback-when-its-command-cannot-run-or-prints-undecodable-bytes/).
   A catch alone is not the fix here, though. It turns the traceback into a
   message while the cards still never reach Claude, so item 1 (or 4) is
   what delivers them. For the same reason, a generic top-level `OSError`
   handler is not this card's fix. The open
   [goc-new-crashes-with-oserror-traceback-on-overlong-title](../goc-new-crashes-with-oserror-traceback-on-overlong-title/)
   shares the traceback symptom but needs an input guard instead.
3. **Update the fake `claude` in `tests/test_terminal_status_guard.py:270-288`.**
   It records argv only (`printf "%s\n" "$@" > "$FAKE_CLAUDE_ARGV"`), and
   `test_quality_pass_llm_keeps_closed_cards_out_of_the_llm_sample` (`:332`)
   reads the prompt back from that file. A stdin fix must capture stdin too.
4. **Optional: bound each call.** One call for 183 cards also asks for 183
   verdict records in a single response. Byte-bounded batches, with their
   verdict lists concatenated, would make the help's "Sonnet-batched"
   literally true. This is not measured here: no API call was made.

A test for item 2 should inject the `OSError`, for example by patching
`subprocess.run`, rather than rely on a fake that cannot exec. While this
card was being written, a no-shebang fake placed ahead of the real CLI fell
through to the real `claude`: after an exec error such as `ENOEXEC`, CPython
moves on to later PATH entries.

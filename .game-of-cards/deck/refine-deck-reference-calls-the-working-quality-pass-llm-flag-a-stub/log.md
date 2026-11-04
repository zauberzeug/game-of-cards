## 2026-11-04T04:30:28Z — Staleness re-check

ea737cb4 (closing
[quality-pass-llm-crashes-once-the-deck-outgrows-one-command-line-argument](../quality-pass-llm-crashes-once-the-deck-outgrows-one-command-line-argument/))
changed the pass this card's section has to describe. It did not fix this
card's defect: `reproduce.py` still exits 1 on all four drift checks,
because `reference.md` still calls the flag a stub and names none of
`--limit`, `--dry-run` or `--yes`.

- **The invocation moved.** `_run_sonnet_quality_pass` now runs
  `claude --model sonnet -p --output-format json` and writes the prompt to
  its stdin. The `-p <prompt>` shape quoted under "What's broken" predates
  ea737cb4, so the rewritten section should not show it.
- **One call, not a batched pass.** The `--llm` help no longer says
  "Sonnet-batched". It says the pass sends every selected live card in one
  `claude -p` call. The section's "Sonnet-batched pass" wording now
  contradicts the help as well as the engine.
- **The prerequisite has its own message.** A missing `claude` reports
  ``ERROR: cannot run claude: the `claude` CLI is not on PATH; --llm needs Claude Code installed and logged in.``
  It no longer says "could not parse Sonnet response".
- **`--limit` is no longer a workaround.** Before ea737cb4, the pass
  crashed on Linux past about 80 cards unless `--limit` capped the sample.
  It now runs on a deck of any size, so the section can present `--limit`
  as the sampling cap the parser documents.

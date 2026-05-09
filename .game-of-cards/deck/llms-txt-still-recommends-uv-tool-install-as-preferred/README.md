---
title: llms-txt-still-recommends-uv-tool-install-as-preferred
summary: "`site/llms.txt:44` reads `uv tool install game-of-cards   # preferred` with `# or: pipx install game-of-cards` on line 45. The recorded baseline (memory `feedback_runtime_baseline_python3.md`) is to prefer broadly-distributed `python3` / `pipx` over the narrower `uv`. `lead-llms-txt-with-claude-code-plugin` (done 2026-05-09) reordered the file so the Claude Code plugin install is the headline path; the secondary section retained the old `# preferred` comment unchanged. `0967798` dropped 'via uv' from a separate description, but did not touch this comment. As llms.txt is the file LLMs ingest to learn how to recommend GoC, this single word miscalibrates downstream agent recommendations."
status: blocked
stage: null
contribution: low
created: 2026-05-09
closed_at: null
human_gate: none
advances:
  - list-game-of-cards-on-anthropic-community-marketplace
advanced_by:
  - validate-plugin-mirror-fails-when-openclaw-omits-hooks-dir
tags: [documentation]
definition_of_done: |
  - [x] `site/llms.txt:44` no longer marks `uv tool install` as `# preferred`
  - [x] The two install lines (uv and pipx) read as peer alternatives, with pipx listed first if either is given precedence (per `feedback_runtime_baseline_python3.md`)
  - [x] No other content in `site/llms.txt` changes — this is a one-comment edit
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# llms.txt still recommends `uv tool install` as preferred

## What's wrong

`site/llms.txt` line 44:

```
uv tool install game-of-cards   # preferred
# or: pipx install game-of-cards
```

The `# preferred` comment recommends the narrower install path
(`uv`) over the broader one (`pipx`, which assumes only `python3`).
The project's recorded baseline is the opposite: prefer `python3` /
`pipx` because they are universally available, and use `uv` only
where dev tooling already requires it.

This file is `llms.txt` (per the [llms.txt convention](https://llmstxt.org)),
so its audience is downstream LLMs that read it to learn how to
recommend GoC. Calibrating that recommendation toward `uv` against
the recorded preference is the entire surface of the bug.

## Suggested edit

```
pipx install game-of-cards
# or: uv tool install game-of-cards
```

The order swap encodes the preference; dropping the `# preferred`
comment removes the override that contradicted it. Implementer can
also keep both lines on equal footing if that reads cleaner — the
key constraint is that `uv` is no longer the recommended option.

## Why this is gate=none

One comment, one line, no design decision. The recorded baseline
already settled the python3-over-uv question.

## Cross-references

- `lead-llms-txt-with-claude-code-plugin` (done) — reordered the
  install sections; missed this nested comment
- Memory `feedback_runtime_baseline_python3.md` — the recorded
  preference for `python3` / `pipx` over `uv`
- `plugin-wrapper-drops-uv` (active per recent commits) — the
  source-code half of the same baseline

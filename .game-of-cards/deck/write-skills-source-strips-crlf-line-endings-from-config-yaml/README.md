---
title: write-skills-source-strips-crlf-line-endings-from-config-yaml
summary: "`_write_skills_source` reads `.game-of-cards/config.yaml` with `Path.read_text()` and writes it back with `Path.write_text()`, so a CRLF-authored config has every line rewritten to LF the first time install/upgrade/mode-switch sets `skills_source:`. The closed card `install-marker-merge-rewrites-crlf-briefing-files-to-lf` already added `_read_text_keep_newline`/`_write_text_keep_newline` and its DoD called for sweeping other write-paths — this one was missed. Fix: route the read/write through those helpers."
status: done
stage: null
contribution: medium
created: "2026-06-23T19:37:08Z"
closed_at: "2026-06-23T19:42:31Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (CR byte count unchanged after `_write_skills_source` on a CRLF config)
  - [x] TDD: a regression test in tests/ writes a CRLF `config.yaml`, runs `_write_skills_source`, and asserts the CR-byte count is preserved while `skills_source:` is updated
  - [x] TDD: an LF-authored config stays LF (no spurious CR introduced)
  - [x] MECHANICAL: `_write_skills_source` reads via `_read_text_keep_newline` and writes via `_write_text_keep_newline`
  - [x] PROCESS: `uv run goc validate` passes and the full `unittest` suite stays green
worker: {who: "claude[bot]", where: main}
---

# `_write_skills_source` strips CRLF line endings from config.yaml

## Location

`goc/install.py` — `_write_skills_source` (lines 1373-1403), specifically
the read at `engine`/install line 1386 and the write at line 1403.

## What's broken

The function's docstring promises it "Treats the config file as
line-oriented text to avoid round-tripping the whole YAML — preserves
comments and ordering that a parser-then-dump would lose." But the
load/store pair re-encodes every line ending:

```python
text = config_path.read_text()        # universal-newline: CRLF -> LF
...
config_path.write_text(new_text)      # writes LF only, never restores CRLF
```

`Path.read_text()` applies universal-newline translation (every `\r\n`
becomes `\n`); `Path.write_text()` emits `\n` unchanged. So when a
consumer's `.game-of-cards/config.yaml` was authored with CRLF endings
(common on Windows checkouts), the *entire file* — including all of the
user's untouched lines — is silently rewritten from CRLF to LF the first
time `goc install`, `goc upgrade`, or a skills-source mode switch calls
this function.

This is precisely the silent round-trip mutation the docstring claims to
avoid: it preserves comment text and ordering but not the file's newline
convention.

## Empirical evidence

Pre-fix, `reproduce.py` showed all four CR bytes stripped (`CR bytes
before: 4` → `after: 0`, "DEFECT CONFIRMED"). Post-fix, the same script
exits 0:

`uv run python .game-of-cards/deck/write-skills-source-strips-crlf-line-endings-from-config-yaml/reproduce.py`:

```
CR bytes before: 4
CR bytes after:  4
--- resulting file (repr) ---
'# GoC project config\r\ndeck_dir: .game-of-cards/deck\r\nskills_source: vendored\r\nsome_key: value\r\n'

OK: CRLF preserved; only the skills_source line changed.
```

The CRLF convention is preserved and only the `skills_source:` line
changed. Regression tests in `tests/test_install.py`
(`test_write_skills_source_preserves_crlf_line_endings`,
`test_write_skills_source_lf_config_stays_lf`) lock both directions in.

## Why it matters

`.game-of-cards/config.yaml` is a **user-owned / evolving** file under the
upgrade ownership model (AGENTS.md): the engine's contract is to never
destroy authored project state. Rewriting a Windows consumer's whole
config to LF on every `goc upgrade` is a noisy, unrequested diff on a file
the consumer owns — exactly the class of silent re-encoding the project
already fixed for AGENTS.md / CLAUDE.md in the closed card
[install-marker-merge-rewrites-crlf-briefing-files-to-lf](../install-marker-merge-rewrites-crlf-briefing-files-to-lf/),
which introduced `_read_text_keep_newline` / `_write_text_keep_newline`
and whose DoD explicitly called for verifying that **no other
install/upgrade write-path silently re-encodes newlines**.
`_write_skills_source` is such a path and was missed by that sweep.

Reachability: `goc install` calls `_write_skills_source` to stamp the
chosen `skills_source` mode; `goc upgrade` and a manual mode switch
re-invoke it. Any of these on a CRLF-authored config triggers the
rewrite.

## Fix

Use the existing newline-preserving helpers (the same ones the marker-merge
fix added), replacing the two re-encoding calls:

```python
text, newline = _read_text_keep_newline(config_path)
...
_write_text_keep_newline(config_path, new_text, newline)
```

`_read_text_keep_newline` returns LF-normalized text (so the existing
regexes are unchanged) plus the detected dominant newline; the matching
writer translates `\n` back to that newline. LF-authored configs stay LF;
CRLF-authored configs stay CRLF.

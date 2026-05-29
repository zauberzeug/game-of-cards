---
title: install-marker-merge-rewrites-crlf-briefing-files-to-lf
summary: "`goc install`/`goc upgrade` merge their guidance block into AGENTS.md/CLAUDE.md via `_append_marker_block`, which reads with `Path.read_text()` and writes with `Path.write_text()`. Both apply universal-newline translation, so a CRLF-authored briefing file has its ENTIRE contents — including the user's text outside the GoC markers — silently normalized to LF on every run. The documented contract promises content outside the markers is preserved; the line-ending bytes are not."
status: done
stage: null
contribution: medium
created: "2026-05-27T08:17:24Z"
closed_at: "2026-05-27T08:27:17Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits non-zero — a CRLF-authored AGENTS.md keeps its CRLF line endings (CR-byte count unchanged) after a marker merge, including user content outside the GoC block.
  - [x] MECHANICAL: `_append_marker_block`, `_strip_goc_block`, and `_strip_claude_import` (`goc/install.py`) preserve the file's existing newline convention rather than forcing LF (e.g. read bytes / detect the dominant newline and re-emit it, or read with `newline=""` and write back with the detected ending). The GoC block content itself may use the file's detected ending.
  - [x] PROCESS: the behavior is consistent with the AGENTS.md "content above or below those markers is preserved" guarantee — verify no other install/upgrade write-path silently re-encodes newlines.
worker: {who: "claude[bot]", where: main}
---

# Marker-merge rewrites a CRLF-authored briefing file to LF

## Location

`goc/install.py:881` (`_append_marker_block`), `:167` (`_strip_goc_block`),
and `:182` (`_strip_claude_import`).

## What was broken

All the functions that mutate AGENTS.md / CLAUDE.md read and wrote with
the text APIs:

```python
text = target.read_text()                     # universal-newline: CRLF -> LF
pattern = re.compile(rf"{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n?", re.DOTALL)
if pattern.search(text):
    target.write_text(pattern.sub(lambda _: block, text))   # writes LF only
```

`Path.read_text()` applies Python's universal-newline translation
(every `\r\n` becomes `\n`), and `Path.write_text()` does not restore the
original ending. So on a CRLF-authored file, *every* line in the file was
rewritten to LF — not just the GoC block, but the user's own content above
and below the markers.

This contradicts the contract stated in `AGENTS.md`:

> `install._append_marker_block` rewrites only the content between
> `<!-- BEGIN GOC vX.Y.Z -->` and `<!-- END GOC -->`. Content above or
> below those markers is preserved across `goc install` / `goc upgrade`.

The *text* outside the block is preserved, but its *bytes* are not — every
CR is dropped.

## Empirical evidence

`reproduce.py` writes a CRLF AGENTS.md with user content above and below an
existing GoC block, runs `_append_marker_block` once, and counts CR bytes.
After the fix the CR count is unchanged and the script exits non-zero
(its "defect reproduced" branch no longer fires):

```
CR bytes before merge: 9
CR bytes after  merge: 9   (expected: still 9)
user content text preserved:        True
user content CRLF line-ending kept: True   (expected True)

No defect: CRLF line endings preserved.
```

## Why it matters

A consumer who authors AGENTS.md / CLAUDE.md on Windows, or whose repo
pins CRLF via `.gitattributes`, gets the entire file silently re-encoded
to LF the first time they run `goc install` or `goc upgrade`. The result
is a noisy, whole-file diff that buries the actual GoC change, and — for a
repo that deliberately enforces CRLF — a spurious line-ending churn the
tool had no business making. Newline handling is an active fault line in
this codebase: the closed card
[cards with Windows line endings vanish from the deck as unterminated](../cards-with-windows-line-endings-vanish-from-the-deck-as-unterminated/)
(commit 19c6e01) fixed the same class of bug in the engine's frontmatter
parser; this is the install-side sibling.

## Fix (applied)

Added two helpers in `goc/install.py`: `_read_text_keep_newline` reads a
file's raw bytes, detects the dominant ending via `_detect_newline`, and
returns LF-normalized text alongside the detected newline;
`_write_text_keep_newline` translates `\n` back to that ending and writes
bytes. Every install/upgrade write-path that mutates an existing file now
routes through this pair instead of `read_text()`/`write_text()`:
`_append_marker_block`, `_strip_goc_block`, `_strip_claude_import`,
`_sync_claude_import` (the unnamed marker-merge sibling for CLAUDE.md), and
`_append_precommit_hook` (the PROCESS sweep turned up that it re-encodes a
CRLF `.pre-commit-config.yaml` the same way). Fresh-file creation paths
keep writing LF — there is no prior convention to preserve.

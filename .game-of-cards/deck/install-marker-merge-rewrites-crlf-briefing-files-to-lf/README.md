---
title: install-marker-merge-rewrites-crlf-briefing-files-to-lf
summary: "`goc install`/`goc upgrade` merge their guidance block into AGENTS.md/CLAUDE.md via `_append_marker_block`, which reads with `Path.read_text()` and writes with `Path.write_text()`. Both apply universal-newline translation, so a CRLF-authored briefing file has its ENTIRE contents — including the user's text outside the GoC markers — silently normalized to LF on every run. The documented contract promises content outside the markers is preserved; the line-ending bytes are not."
status: open
stage: null
contribution: medium
created: "2026-05-27T08:17:24Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits non-zero — a CRLF-authored AGENTS.md keeps its CRLF line endings (CR-byte count unchanged) after a marker merge, including user content outside the GoC block.
  - [ ] MECHANICAL: `_append_marker_block`, `_strip_goc_block`, and `_strip_claude_import` (`goc/install.py`) preserve the file's existing newline convention rather than forcing LF (e.g. read bytes / detect the dominant newline and re-emit it, or read with `newline=""` and write back with the detected ending). The GoC block content itself may use the file's detected ending.
  - [ ] PROCESS: the behavior is consistent with the AGENTS.md "content above or below those markers is preserved" guarantee — verify no other install/upgrade write-path silently re-encodes newlines.
---

# Marker-merge rewrites a CRLF-authored briefing file to LF

## Location

`goc/install.py:881` (`_append_marker_block`), `:167` (`_strip_goc_block`),
and `:182` (`_strip_claude_import`).

## What's broken

All three functions that mutate AGENTS.md / CLAUDE.md read and write with
the text APIs:

```python
text = target.read_text()                     # universal-newline: CRLF -> LF
pattern = re.compile(rf"{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n?", re.DOTALL)
if pattern.search(text):
    target.write_text(pattern.sub(lambda _: block, text))   # writes LF only
```

`Path.read_text()` applies Python's universal-newline translation
(every `\r\n` becomes `\n`), and `Path.write_text()` does not restore the
original ending. So on a CRLF-authored file, *every* line in the file is
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
existing GoC block, runs `_append_marker_block` once, and counts CR bytes:

```
CR bytes before merge: 9
CR bytes after  merge: 0   (expected: still 9)
user content text preserved:        True
user content CRLF line-ending kept: False   (expected True)

DEFECT REPRODUCED: 9 CR bytes silently dropped; the whole file was rewritten LF-only.
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

## Fix

Preserve the file's existing newline convention. One approach: read the
raw bytes (or read with `open(..., newline="")` so translation is
suppressed), detect whether the dominant ending is `\r\n` or `\n`, perform
the marker substitution, then write back with that ending. Apply the same
fix to `_strip_goc_block` and `_strip_claude_import`, which share the
defect. Do not assume LF.

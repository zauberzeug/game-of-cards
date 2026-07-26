---
title: bom-prefixed-card-readme-silently-vanishes-from-every-deck-view
status: open
stage: null
contribution: medium
created: "2026-07-22T13:18:57Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "A UTF-8 BOM (`EF BB BF`) before the opening `---` makes `parse_frontmatter` take the silent no-frontmatter path, so the card vanishes from the queue, `--json`, and every listing with exit 0 and NO per-card warning — while `goc validate` and the title verbs misdiagnose it as \"missing opening '---' at line 1\" even though the delimiter IS at line 1, hidden behind an invisible codepoint."
definition_of_done: |
  - [ ] PROCESS: the handling is chosen from "## Decision required" (tolerate-and-strip vs reject-with-warning) and the gate is lowered to `none` via `goc decide`.
  - [ ] TDD: reproduce.py prints no `[FAIL]` (the BOM card no longer silently vanishes; either it loads, or a per-card warning names the BOM).
  - [ ] TDD: a regression test covers a BOM-prefixed README across the queue read, `goc validate`, and one title verb — no surface may drop the card silently, and any error message must name the BOM rather than a missing `---`.
  - [ ] MECHANICAL: plugin engine mirrors re-synced (`python scripts/sync_plugin_assets.py --check` clean).
  - [ ] PROCESS: `uv run goc validate` passes.
---

# BOM-prefixed card README silently vanishes from every deck view

## Location

`goc/engine.py:181` (`parse_frontmatter` opener check), downstream
`load_card` (`goc/engine.py:944`) and `load_all_cards`
(`goc/engine.py:966`).

## What's broken

`parse_frontmatter` decides "this file has no frontmatter at all" by a
literal prefix check:

```python
if not (text.startswith("---\n") or text.startswith("---\r\n")):
    return {}, text
```

A README whose bytes begin with the UTF-8 BOM `EF BB BF` (i.e.
`"﻿---\n..."` after decoding) fails both prefixes, so the parser
returns the legitimate-non-card-file result `({}, text)` instead of
raising `FrontmatterError`. `load_card` then drops the card
(`if not fm: return None`), and `load_all_cards` only prints its
per-card warning for `FrontmatterError`, so nothing reaches stderr.
The docstring's own contract for that return path is "No opening `---`
at line 1 → returns ({}, text) (non-frontmatter file)" — but here the
opening `---` IS at line 1; only an invisible codepoint precedes it.

The two surfaces that do say something are misleading:
`validate_deck_directories` and `load_card_or_exit` report
`"README.md has no frontmatter (missing opening '---' at line 1)"`,
pointing the reader at a delimiter that is present.

## Empirical evidence

`uv run python .game-of-cards/deck/bom-prefixed-card-readme-silently-vanishes-from-every-deck-view/reproduce.py`:

```
== queue BEFORE BOM ==
TITLE           STATUS  CONTR.  VALUE  GATE  TAGS  DOD
--------------  ------  ------  -----  ----  ----  ---
bom-probe-card  open    medium    3.0  none  bug   0/1
== queue AFTER BOM ==
(empty)
stderr: (empty)   exit: 0
== goc validate ==
ERROR: bom-probe-card: README.md has no frontmatter (missing opening '---' at line 1)

[FAIL] BOM card vanished silently (exit 0, no warning); validate blames a missing '---' that IS at line 1.
```

## Why it matters

**Reachability:** the BOM is what Windows Notepad and PowerShell 5.x
`Set-Content -Encoding UTF8` prepend when saving — the same
Windows-authoring path already documented on the open sibling
[cards-with-windows-line-endings-vanish-from-the-deck-as-unterminated](../cards-with-windows-line-endings-vanish-from-the-deck-as-unterminated/).
That sibling takes the `FrontmatterError` path, which at least prints a
per-card WARNING on every queue read; the BOM takes the strictly worse
silent path. A card a human authored and committed on Windows simply
stops existing for the scheduler — no queue entry, no board glyph, no
warning — until someone happens to run `goc validate`, whose message
then sends them hunting for a `---` that is already there.

## Decision required

Both fixes are one-site changes in `parse_frontmatter`; the pick is a
policy call, and it should be made consistently with the open sibling
CRLF card's decision:

1. **Tolerate and strip.** Remove a leading `﻿` (after decoding)
   before the prefix check — BOM cards parse and load normally,
   matching how most editors treat the BOM as a no-op. Cheapest for
   users; the file keeps round-tripping with its BOM until some verb
   rewrites it.
2. **Reject loudly.** Detect the `﻿` prefix and raise
   `FrontmatterError("UTF-8 BOM before opening '---' ...")` — the card
   still doesn't load, but every queue read prints the per-card
   warning naming the actual byte-level cause, and validate stops
   blaming a missing delimiter. Keeps the card-file bytes invariant
   strict.

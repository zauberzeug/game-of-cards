---
title: cards-with-windows-line-endings-vanish-from-the-deck-as-unterminated
summary: "A card whose README.md uses Windows (CRLF) line endings is silently dropped from every queue and board. The frontmatter opener guard accepts `---\\r\\n`, but FRONTMATTER_RE only matches LF separators, so parse_frontmatter raises FrontmatterError(\"unterminated\") on structurally valid input — and load_all_cards warns-and-skips it. Decide whether to normalize CRLF on read or reject it cleanly."
status: open
stage: null
contribution: medium
created: "2026-05-27T08:00:31Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded in this README (normalize-on-read vs reject-cleanly) with rationale in log.md.
  - [ ] TDD: reproduce.py exits zero (CRLF card parses or is rejected per the decision, with no misleading "unterminated" diagnostic).
  - [ ] TDD: a regression test asserts the chosen behavior for a CRLF-authored README (parses to the same (data, body) as the LF twin, OR fails with a CRLF-naming diagnostic).
  - [ ] MECHANICAL: the opener guard at engine.py:151 and FRONTMATTER_RE at engine.py:130 no longer contradict each other; `goc validate` clean; plugin-asset sync `--check` green.
---

# Cards with Windows line endings vanish from the deck as unterminated frontmatter

## Location

- `goc/engine.py:130` — `FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)`
- `goc/engine.py:151` — opener guard `if not (text.startswith("---\n") or text.startswith("---\r\n")):`
- `goc/engine.py:609-613` — `load_all_cards` catches `FrontmatterError`, warns to stderr, and `continue`s (drops the card).

## What's broken

The opener guard in `parse_frontmatter` deliberately accepts **both** LF and
CRLF openers:

```python
if not (text.startswith("---\n") or text.startswith("---\r\n")):
    return {}, text
```

The presence of the `"---\r\n"` branch is a clear signal that CRLF-authored
cards are meant to be parsed. But the regex that actually extracts the
frontmatter only matches **LF** separators:

```python
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
```

A CRLF file's bytes are `---\r\n...\r\n---\r\n...`. `^---\n` cannot match
`---\r\n` (a `\r` sits between `---` and the `\n`), so `m` is `None` and the
function raises:

```
FrontmatterError: frontmatter unterminated: opening '---' at line 1 has no
matching closing '---' delimiter
```

The diagnostic is misleading — the frontmatter *is* terminated; it just uses
CRLF. Downstream, `load_all_cards` (engine.py:609-613) catches the exception,
prints a per-card WARNING to stderr, and skips the card. So a structurally
valid card authored on Windows (or via an editor configured for CRLF)
**silently disappears from every `goc` queue and board**, and `goc validate`
reports it as "unterminated."

## Empirical evidence

`uv run python deck/cards-with-windows-line-endings-vanish-from-the-deck-as-unterminated/reproduce.py`:

```
=== LF (control) ===
parsed: {'status': 'open', 'title': 'x'} | body: 'body here\n'

=== CRLF (same content, Windows line endings) ===
opener guard accepts CRLF: True
RAISED FrontmatterError: frontmatter unterminated: opening '---' at line 1 has no matching closing '---' delimiter

RESULT: DEFECT PRESENT — opener guard accepted '---\r\n' but the regex
rejected it as unterminated. load_all_cards() will warn-and-drop this card
from every queue/board.
```

Same content, only the line endings differ: LF parses; CRLF raises. Exit code 1.

## Why it matters

A card silently vanishing from the deck is the worst failure mode for a
work-tracking tool — the work isn't refused loudly, it just isn't there. A
contributor on Windows, or anyone whose editor/git config produces CRLF,
authors a card, sees a stderr warning they may not notice, and the card never
appears in the queue. The `api-contract` tag applies because the frontmatter
format is the contract consumers and plugin payloads depend on, and the
opener guard already advertises CRLF as part of that contract.

## Decision required

The fix path needs a contract call: **should GoC support CRLF-authored card
files, or reject them cleanly?**

- **Option A — Normalize CRLF→LF on read (recommended).** Strip `\r` (or
  normalize line endings) at the top of `parse_frontmatter` before the regex
  runs, so a CRLF card parses identically to its LF twin. This honors the
  intent already encoded in the opener guard and is the friendliest to
  cross-platform authors. Risk: trailing `\r` could leak into body content if
  normalization is incomplete — normalize the whole text, not just the
  delimiters.
- **Option B — Reject CRLF cleanly.** Remove the `"---\r\n"` branch from the
  opener guard and have `goc validate` emit a CRLF-naming diagnostic ("card
  uses Windows line endings; convert to LF"). Cheaper, but pushes the burden
  onto authors and contradicts the guard's current stated intent.

Either way the current state — guard says yes, regex says no, card vanishes —
is wrong. The recommended path is **Option A** (normalize on read): it removes
a whole class of silent-disappearance bugs and matches the guard's existing
promise. The decision determines what `reproduce.py` should assert on success
(parses-clean vs fails-with-clear-message).

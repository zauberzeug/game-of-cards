---
title: trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir
status: open
stage: null
contribution: medium
created: "2026-07-22T01:47:18Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: goc new (and goc move, and validate_card) check titles with re.match against title_pattern, whose $ anchor matches before a trailing newline — so goc new "newline-tail\n" exits 0 and scaffolds a card directory literally named with an embedded newline. The card is unaddressable by its visible name (goc show newline-tail fails), its title emits as a block scalar, listings print a stray blank line, and goc validate reports OK.
definition_of_done: |
  - [ ] PROCESS: decision recorded — anchor title_pattern in schema.yaml with \Z vs switch the three re.match call sites to re.fullmatch
  - [ ] TDD: reproduce.py exits zero (goc new rejects the trailing-newline title with exit 2)
  - [ ] TDD: regression test covers goc new, goc move, and validate_card all rejecting titles with a trailing newline
  - [ ] MECHANICAL: if schema.yaml changes, the inlined card-schema skill copy and plugin mirrors are re-synced
---

# trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir

`goc new $'newline-tail\n'` exits 0 and creates
`.game-of-cards/deck/newline-tail\n/` — a directory whose name ends in
a real newline.

## Location

- `goc/schema.yaml:22` — `title_pattern: "^[a-z0-9][a-z0-9-]*[a-z0-9]$"`
- `goc/engine.py:5469` — `_cmd_new`: `if not re.match(schema.title_pattern, title):`
- `goc/engine.py:5932` — `_cmd_move`: same check for the rename target
- `goc/engine.py:1639` — `validate_card`: same check on the stored title

## What's broken

Python's `$` matches before a trailing newline, so
`re.match(title_pattern, "newline-tail\n")` succeeds at all three
sites. Consequences observed empirically:

- `goc new $'newline-tail\n'` exits 0; `ls -b` shows the escaped
  directory name `newline-tail\n`.
- The README frontmatter carries `title: |` — a block scalar, because
  the emitter must preserve the trailing newline.
- `goc show newline-tail` exits 2 with "README.md not found"; only the
  exact `$'newline-tail\n'` argument addresses the card.
- `goc validate` prints `OK  newline-tail` followed by a stray blank
  line (the embedded newline garbling table output) and exits 0 — the
  stored title round-trips with the newline and passes the same
  `$`-anchored check again.
- `goc status $'newline-tail\n' active` claims and auto-commits the
  malformed path.
- The `TITLE_ANTIPATTERNS` jargon guard (engine.py:5374) never fires:
  its character class deliberately admits `\s`, which includes `\n`.

## Why it matters

A single shell-quoting slip (command substitution capturing its
trailing newline, e.g. `goc new "$(some-slug-generator)"`) persists a
card directory that no title-addressed verb can reach by its visible
name, that garbles every listing that prints titles, and that
`validate` certifies as OK. Reachability: any `goc new` / `goc move`
argument produced by `$(...)` capture or editor copy-paste.

Same root cause (`$`-anchored validation regex) as
[waiting-until-with-trailing-newline-passes-wait-then-crashes-reads](../waiting-until-with-trailing-newline-passes-wait-then-crashes-reads/),
but a different validator with a different blast radius — this one
corrupts the on-disk deck namespace instead of crashing readers.

## Decision required

Two credible fix paths; a human should pick because `title_pattern` is
a published contract surface (inlined into the `card-schema` skill and
read by consumers):

1. **Change the pattern**: `title_pattern: "^[a-z0-9][a-z0-9-]*[a-z0-9]\\Z"`
   in `goc/schema.yaml:22`. One edit fixes all three call sites and any
   future consumer, but changes the published pattern string (consumers
   that embed it in non-Python regex engines may not support `\Z`).
2. **Change the call sites**: switch the three `re.match(...)` calls to
   `re.fullmatch(...)` in `goc/engine.py` (5469, 5932, 1639). Keeps the
   published pattern untouched; every consumer of `title_pattern`
   outside these three sites keeps the latent hole.

Either way, `validate_card` should FAIL (not OK) a stored title with a
trailing newline so legacy decks surface the corruption.

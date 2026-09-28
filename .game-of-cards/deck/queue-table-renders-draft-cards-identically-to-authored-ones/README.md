---
title: queue-table-renders-draft-cards-identically-to-authored-ones
summary: "UNVERIFIED. goc --status all is the only table that lists draft scaffolds, and the docs name it as where drafts appear, but the table's rows carry no draft cell at any verbosity, while the board marks drafts with a pencil glyph and JSON carries draft: true. A reader deduping against goc --status all, as create-card instructs, cannot tell that a matching title is an unauthored placeholder."
status: open
stage: null
contribution: medium
created: "2026-09-28T01:36:46Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py renders `goc --status all` (at `-v` 0, 1 and 2) over a deck holding one draft and one authored open card and asserts the table tells them apart — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] TDD: a regression test pins a draft marker in the table (the board's `✎`, in the title cell or a column), consistent with the board and the JSON `draft` field
  - [ ] MECHANICAL: `card-schema/SKILL.md:146` and `card-schema/reference.md:67-69` name the table marker next to the board's; drop the `unverified` tag once reproduce.py lands
---

# The queue table renders draft cards identically to authored ones

> **UNVERIFIED.** Surfaced by an audit hunter on the engine query/render
> seam on 2026-09-28. The filing agent re-read and confirmed the
> citations. No `reproduce.py` was written this round; the falsification
> recipe is below.

## Location

All in `goc/engine.py` unless noted:

- `:3076-3077`: unauthored scaffolds "are hidden from every listing
  except `--status all`". So `--status all` is the one table where drafts
  appear.
- `:3419` and `:3421`: the table's row tuples (`-v` and default) carry no
  draft cell. The `-vv` detail block adds no draft line either.
- `:3662-3663`: the board marks them, with `if is_draft: marker += " ✎"`.
- `:3550` and `:3582`: JSON carries `"draft": card_is_draft(t)`.
- `goc/templates/skills/card-schema/SKILL.md:146`: "hidden from queues
  (visible under `--status all`, `✎` on the board)". Also
  `card-schema/reference.md:67-69`: "surfaced only under
  `goc --status all`, marked `✎` on the board".

## Hypothesis

At every verbosity, the table renders a draft exactly like an authored
open card. The board and JSON both distinguish them, so the one view the
docs name for seeing drafts is also the one view that cannot show which
rows are drafts. The hunter's scratch deck rendered
`authored-card  open … none … 0/1` and `scaffold-card  open … none … 0/1`
identically under `goc --status all -vv`, while the board showed
`scaffold-card [m] ✎` and `--json --slim` gave `draft: true`.

This matters because `--status all` is create-card's dedup view
(`create-card/SKILL.md:63`, `goc --status all | grep -i <fragment>`) and
scan-deck's "everything" view (`scan-deck/SKILL.md:150`). A reader
deduping against the table cannot tell that a matching title is an
unauthored placeholder. That is the kind of title-only judgement the
draft flag exists to prevent. The closed sibling
`queue-table-omits-the-waiting-on-and-waiting-until-impediment-overlay`
fixed the same kind of table-only gap for the impediment overlay.

## Why deferred

The citations are confirmed. No `reproduce.py` is committed this round.
Where the marker goes (a suffix on the title cell, as the board does, or
a column) is left to the implementing agent.

## Falsification recipe

In a scratch deck, run `goc new scaffold-card` (it stays a draft) and file
and publish one authored card. Run `goc --status all`, `-v` and `-vv`. If
any of them distinguishes `scaffold-card`, the hypothesis is disproved.

Surfaced by: general-purpose audit hunter (engine query / render
surface), 2026-09-28.

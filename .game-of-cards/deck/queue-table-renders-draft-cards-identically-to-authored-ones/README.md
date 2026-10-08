---
title: queue-table-renders-draft-cards-identically-to-authored-ones
summary: "goc --status all is the only table that lists draft scaffolds, and create-card dedups against it with grep, yet the table rendered a draft exactly like an authored card at every verbosity while the board marked it with a pencil glyph and JSON carried draft: true. The table now suffixes a draft's TITLE cell with the board's glyph, and table, board and JSON all key the mark on card_is_draft, so the three views mark the same cards."
status: done
stage: null
contribution: medium
created: "2026-09-28T01:36:46Z"
closed_at: "2026-10-08T05:38:19Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py renders `goc --status all` (at `-v` 0, 1 and 2) over a deck holding one draft and one authored open card and asserts the table tells them apart — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] TDD: a regression test pins a draft marker in the table (the board's `✎`, in the title cell or a column), consistent with the board and the JSON `draft` field
  - [x] MECHANICAL: `card-schema/SKILL.md:146` and `card-schema/reference.md:67-69` name the table marker next to the board's; drop the `unverified` tag once reproduce.py lands
worker: {who: "claude[bot]", where: main}
---

# The queue table renders draft cards identically to authored ones

## Location

All in `goc/engine.py` unless noted:

- `:3167` (`filter_cards`): drafts are hidden from every listing except
  `--status all`, so `--status all` is the one table where they appear.
- `:3530` (`render_table`): the TITLE cell. Before the fix the row tuples
  carried `t.title` bare at every verbosity, and the `-v` / `-vv` detail
  block had no draft line either.
- `:3781-3783` (`render_board`): the board's draft mark, `✎`.
- `:3664` and `:3696` (`render_json`): `"draft": card_is_draft(t)`.
- `:2799`: `DRAFT_MARKER`, the glyph both renderers now share.
- `goc/templates/skills/card-schema/SKILL.md:146` and
  `card-schema/reference.md:68-72`: the docs said drafts are "visible
  under `--status all`, `✎` on the board", and named no table marker.

## What was broken

`goc --status all` is the view `Skill(create-card)` dedups against
(`goc --status all | grep -i <fragment>`) and the view
`Skill(scan-deck)` lists as "everything". It is also the only table
that lists draft scaffolds. Yet a draft and an authored card rendered
identically there at every verbosity, while the board marked the draft
`✎` and `--json` carried `draft: true`. A reader deduping against the
table could not tell that a matching title was an unauthored
placeholder. The draft flag exists to prevent exactly that title-only
judgement. The closed sibling
[queue-table-omits-the-waiting-on-and-waiting-until-impediment-overlay](../queue-table-omits-the-waiting-on-and-waiting-until-impediment-overlay/)
fixed the same kind of table-only gap for the impediment overlay.

## Empirical evidence

`reproduce.py` writes two cards that match in every rendered field
(status, contribution, gate, tags, created, summary, DoD, body) and
differ only in the title and `draft: true`. It runs the real CLI at
`-v` 0, 1 and 2, masks the titles, and compares the two row blocks.
Before the fix:

```
=== goc --status all === draft distinguishable: False
  TITLE          STATUS  CONTR.  VALUE  GATE  TAGS   DOD
  -------------  ------  ------  -----  ----  -----  ---
  authored-card  open    medium    3.0  none  story  0/1
  scaffold-card  open    medium    3.0  none  story  0/1
...
DEFECT: 3 table view(s) render the draft and the authored card identically once the titles are masked: goc --status all; goc --status all -v; goc --status all -vv
  the board marks the draft ✎ and --json carries draft: true
exit=1
```

After the fix (`-vv` shown; `-v` and the terse table get the same TITLE
cell):

```
=== goc --status all -vv === draft distinguishable: True
  TITLE            STATUS  STAGE  CONTR.  VALUE  GATE  CREATED               TAGS   DOD
  ---------------  ------  -----  ------  -----  ----  --------------------  -----  ---
  authored-card    open    -      medium    3.0  none  2026-09-28T00:00:00Z  story  0/1
      summary: One summary shared by both cards.
      - [ ] TDD: one criterion shared by both cards
  scaffold-card ✎  open    -      medium    3.0  none  2026-09-28T00:00:00Z  story  0/1
      summary: One summary shared by both cards.
      - [ ] TDD: one criterion shared by both cards

=== verdict ===
OK: every --status all table verbosity tells the draft from the authored card
exit=0
```

## Fix (applied)

- **Table.** `render_table` suffixes a draft's TITLE cell with
  `DRAFT_MARKER` at every verbosity. The mark goes inside the cell
  before the widths are computed, so the column widens and every other
  cell stays aligned with the header.
- **One glyph, one predicate.** `DRAFT_MARKER = "✎"` sits next to
  `card_is_draft`, and both renderers use it. The table, the board and
  the JSON `draft` field all key on `card_is_draft` alone, so a card is
  marked in one view iff it is marked in the other two.
- **Board.** The board's mark used to be gated on `live` (a non-terminal
  status). That gate made a difference only for a terminal card still
  flagged `draft: true`. `goc validate` rejects that state, but a hand
  edit can produce it, and `--done` then hides the card as a draft. JSON
  already said `draft: true` for it, so the board now marks it too. The
  `⏳` not-ready glyph is still live-gated on its own, and a live draft
  still shows `✎` instead of `⏳`.
- **Docs.** `card-schema/SKILL.md`, `card-schema/reference.md` and
  `create-card/reference.md` § Draft contract name the table mark next
  to the board's.

### Why the title cell, not a column

- A title-cell mark is what the board already does.
- It shows at every verbosity, including the terse table that a
  `goc --status all | grep` dedup reads.
- `grep` returns whole lines, so the mark lands on the matched line.
- A DRAFT column would be empty on nearly every row and would widen
  every table. The sibling card rejected a mostly-null column for the
  impediment overlay for the same reason.
- No consumer parses the table by column position. The skills and
  workflows read `--json`, and the dedup flow is a line `grep`. The
  title stays the row's first whitespace-separated token.

## Artifacts

- `reproduce.py`: exits 0 once every `--status all` verbosity tells the
  draft from the authored card. It exited 1 before the fix.
- `tests/test_queue_table_draft_marker.py`: pins the TITLE-cell mark at
  `-v` 0, 1 and 2, column alignment, table/board/JSON agreement over a
  six-card deck (including gated, active and done cards), the
  terminal-draft case, and that a live gated draft still shows `✎`
  instead of `⏳`.

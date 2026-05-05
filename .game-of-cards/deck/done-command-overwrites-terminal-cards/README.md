---
title: done-command-overwrites-terminal-cards
summary: "`goc done` can be run on cards already in other terminal states (`disproved` and `superseded`), rewriting their forensic status to `done` and stamping `closed_at`. That erases the terminal meaning recorded by the prior investigation or supersession."
status: open
stage: null
contribution: high
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] `uv run python deck/done-command-overwrites-terminal-cards/reproduce.py` exits zero
  - [ ] `goc done` refuses cards currently in terminal non-done states (`disproved`, `superseded`)
  - [ ] The refusal message tells the user to use the appropriate supersede/disprove workflow instead of closing
  - [ ] Focused regression coverage proves `disproved` and `superseded` cards keep their status when `goc done` is attempted
---

# done-command-overwrites-terminal-cards

## Location

- `goc/templates/skills/card-schema/SKILL.md:49`
- `goc/templates/skills/card-schema/SKILL.md:50`
- `goc/templates/skills/card-schema/SKILL.md:51`
- `goc/engine.py:1286`
- `goc/engine.py:1302`
- `goc/engine.py:1303`

## What's broken

The schema reference defines `done`, `disproved`, and `superseded` as
terminal states. `goc done` enforces DoD checkboxes, but it does not
check the current status before forcing:

```python
text = mutate_frontmatter_field(text, "status", "done")
text = mutate_frontmatter_field(text, "closed_at", today)
```

As a result, a card that was terminal because the hypothesis was
disproved or the work was superseded can be rewritten to `done`.

## Empirical evidence

Current output from `uv run python deck/done-command-overwrites-terminal-cards/reproduce.py`:

```text
disproved-card: exit=0; stdout=disproved-card: disproved → done; status: done; closed_at: 2026-05-04
superseded-card: exit=0; stdout=superseded-card: superseded → done; status: done; closed_at: 2026-05-04
defect present: goc done overwrote terminal cards: disproved-card, superseded-card
```

## Why it matters

`disproved` and `superseded` preserve different forensic facts than
`done`. Converting them to `done` makes the deck claim work completed
successfully when the real history was "ruled out" or "replaced by
something else".

This is a sibling of
[`status-command-reopens-terminal-cards`](../status-command-reopens-terminal-cards/):
that card covers the generic `status` command moving terminal cards
backward; this one covers the `done` command overwriting terminal cards.

## Fix

In `done()`, reject current statuses `disproved` and `superseded` before
mutating frontmatter. Also keep the already-done idempotency fix tracked
in [`done-rerun-rewrites-closure-date`](../done-rerun-rewrites-closure-date/)
so `done` handles every terminal source state deliberately.

---
title: goc-quality-pass-reports-a-clean-deck-in-a-repo-that-has-no-deck
summary: "In a repo with no deck, goc quality-pass prints Quality pass over 0 cards with both checks clean, exit 0, and nothing on stderr. It is a read view that never got the missing-deck notice the queue view and goc triage print, so an unscaffolded repo or a wrong cwd reads as a clean deck instead of one that does not exist."
status: done
stage: null
contribution: low
created: "2026-11-19T04:44:45Z"
closed_at: "2026-11-19T04:52:25Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits 0. `goc quality-pass` at `--status open` and at `--status all` print the default view's missing-deck notice line on stderr, and exit 0 and the zero-card stdout stay unchanged.
  - [x] TDD: `tests/test_missing_deck_notice.py` covers `goc quality-pass` in a repo with no deck and stays silent on an existing deck. The new case fails on the engine before the fix.
  - [x] MECHANICAL: `_cmd_quality_pass` calls `_note_missing_deck()`, the helper the queue view and `goc triage` call, rather than a copy of the notice. Plugin mirrors are re-synced.
worker: {who: "claude[bot]", where: main}
---

# `goc quality-pass` reports a clean deck in a repo that has no deck

Surfaced while working
[goc-triage-reports-no-parked-cards-in-a-repo-that-has-no-deck](../goc-triage-reports-no-parked-cards-in-a-repo-that-has-no-deck/):
its survey of every engine verb in a repo with no deck found this gap. It is
fixed through in the same session, as its own card and commit.

## Location

At `5475e43d`, `goc/engine.py:5496` `_cmd_quality_pass` loads the deck at
`:5508` with `cards = load_all_cards()` and never checks whether the deck
exists.
`load_all_cards()` returns `[]` both for an empty deck and for no deck at all,
so with no deck Layer 1 runs over zero cards and prints `Title antipatterns:
clean.` (`:5532`) and `Missing summary: clean.`

The queue view and `goc triage` print the notice first, through
`_note_missing_deck()` (`:4943`, called at `:4975` and `:8122`). Its docstring
states the contract:

> Every read view calls this before it loads the deck, because
> `load_all_cards()` returns `[]` for no deck and for an empty one alike, so
> without the notice a repo with no deck renders exactly like an empty queue.

`tests/test_missing_deck_notice.py` opens with the same contract: "A read view
in a repo without a deck names the missing deck." Layer 1 of `quality-pass`
is a read view, and nothing in that module runs it.

## Empirical evidence

`reproduce.py` on `476f0b2f` with the triage fix in the working tree, in a
fresh `git init` directory with no `.game-of-cards/`:

```
--- control: goc (default view)  exit=0
stdout: 'No cards match (status: open).'
stderr: 'goc: no Game of Cards deck found from /tmp/tmpg6cn544l upward (no such file or directory: .game-of-cards/deck/). Run `goc install` at the intended project root first (agents: invoke Skill(kickoff)).'
--- goc quality-pass  exit=0
stdout: 'Quality pass over 0 cards (status=open):\n\nTitle antipatterns: clean.\n\nMissing summary: clean.'
stderr: ''
--- goc quality-pass --status all  exit=0
stdout: 'Quality pass over 0 cards (status=all):\n\nTitle antipatterns: clean.\n\nMissing summary: clean.'
stderr: ''

[FAIL] defect fires:
 - goc quality-pass: no missing-deck notice on stderr
 - goc quality-pass --status all: no missing-deck notice on stderr
```

## Why it matters

`Skill(refine-deck)`'s card-metadata step runs `goc quality-pass --status all`
to find jargon titles and missing summaries. Run from the wrong directory or
in a checkout that was never scaffolded, it answers that every check is clean,
which reads as a deck with nothing to tidy. Nothing says that no deck was read.

The damage is small. Inside refine-deck the Preflight still routes to
`Skill(kickoff)`, because the skill's preamble runs queue views that do print
the notice. So this card is `low`. The cost falls on a human or script that
runs the verb directly.

## Fix

`_cmd_quality_pass` now calls `_note_missing_deck()` just before
`load_all_cards()`. That is the helper the queue view and `goc triage` call, so
the notice line is the same. It goes to stderr only: the exit code and the
zero-card stdout are unchanged, and an existing deck keeps it silent. `--llm`
mode gets the notice too, since it shares the load. After the fix,
`reproduce.py` exits 0.

`tests/test_missing_deck_notice.py` gains
`test_quality_pass_names_the_missing_deck_like_the_queue_view`, which fails
before the fix, and `test_quality_pass_stays_silent_on_an_existing_deck`.

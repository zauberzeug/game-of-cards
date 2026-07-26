---
title: symlinked-card-dir-loads-in-queues-but-every-title-verb-rejects-it
status: open
stage: null
contribution: medium
created: "2026-07-22T01:47:18Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: A deck entry that is a symlink to a directory outside the deck is listed by the queue/board and passes goc validate (load_all_cards follows symlinks), but every title-addressed verb — show, status, done, wait, advance — exits 2 with "invalid card title ... not a path" because resolve_card_dir's containment check resolves the symlink and sees a parent outside the deck. The read and mutate surfaces disagree about whether the card exists, and the error message misdescribes a bare directory name as a path.
definition_of_done: |
  - [ ] PROCESS: decision recorded — which surface changes: loaders/validate flag symlinked deck entries, or resolve_card_dir accepts them, or symlinks are rejected everywhere with an accurate message
  - [ ] TDD: reproduce.py exits zero (the listing, validate, and title-verb surfaces agree on symlinked deck entries)
  - [ ] TDD: regression test pins the agreed behavior for a symlinked card directory
---

# symlinked-card-dir-loads-in-queues-but-every-title-verb-rejects-it

A card directory that is a symlink (target outside the deck) is
first-class to the read surfaces and invisible to the verb surfaces.

## Location

- `goc/engine.py:1033-1036` — `resolve_card_dir`:
  `or (DECK_DIR / title).resolve().parent != DECK_DIR.resolve()` —
  `.resolve()` follows the symlink, so the containment check fails and
  the verb exits with `invalid card title 'sym-card' — a title is the
  bare card directory name inside the deck, not a path`.
- `goc/engine.py:970-971` — `load_all_cards`:
  `for sub in sorted(DECK_DIR.iterdir()): if not sub.is_dir(): continue`
  — `is_dir()` follows symlinks, so the same entry loads for the queue,
  the board, and `validate_card` (which compares `fm["title"]` against
  the symlink's own name and passes).

## What's broken

Empirically, with `ln -s /tmp/elsewhere-card .game-of-cards/deck/sym-card`:

- `goc --status all` lists `sym-card` in the table.
- `goc validate` prints `OK  sym-card` and exits 0.
- `goc show sym-card` exits 2 with the "invalid card title … not a
  path" error — as do `status`, `done`, `wait`, `advance`, and every
  other title-addressed verb that goes through `resolve_card_dir`.

The read/validate surfaces and the mutate surfaces contradict each
other about whether the card exists, leaving a visible card no verb
can manage. The error message is also wrong on its face: the argument
IS the bare card directory name inside the deck, not a path.

## Why it matters

Symlinking a card directory is a plausible consumer move (sharing a
card between worktrees, staging a card from a scratch area), and the
failure mode is maximally confusing: the deck says the card is there
and valid, while every verb insists the title is malformed.
Reachability: `resolve_card_dir`'s containment check was added by
[path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck](../path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck/)
to stop path-escape titles; the symlink false-rejection and the
loader/verb disagreement are an unhandled side effect of resolving
before comparing, not covered by that card.

## Decision required

Three credible directions; a human should pick the intended contract:

1. **Reject symlinks everywhere** — `load_all_cards` and `validate`
   skip/flag symlinked entries, `resolve_card_dir` keeps rejecting but
   with an accurate message ("card directory is a symlink out of the
   deck"). Tightest security posture, consistent with the path-escape
   card's intent.
2. **Accept symlinks everywhere** — `resolve_card_dir` compares the
   *lexical* parent (`(DECK_DIR / title).parent`) for containment and
   only resolves for the escape check on the title string itself.
   Preserves the sharing use case; weakens the escape guard's blast
   radius.
3. **Status quo plus honest surfaces** — keep rejecting in
   `resolve_card_dir` but make the loaders skip symlinked entries so
   no surface advertises a card the verbs refuse, and fix the
   misleading error message.

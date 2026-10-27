---
title: goc-done-closes-cards-whose-created-stamp-was-overwritten
summary: "An agent that fills a fresh scaffold by rewriting README.md wholesale drops the created stamp goc new wrote, and publish, status and done released such a card anyway; only goc validate noticed, after the session that could still say when the card was filed had ended."
status: done
stage: null
contribution: medium
created: "2026-10-27T06:21:32Z"
closed_at: "2026-10-27T06:22:04Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: `publish`, `status`, `done` and `done --bundle` restore a missing `created` from the earlier of the card directory's birth time and the commit that first added README.md, and say so in their output.
  - [x] TDD: with no evidence the same verbs refuse (exit 2) and leave the card untouched; the current time is never written.
  - [x] TDD: the `goc new` next-step hint tells the agent to edit the scaffold in place and keep the generated frontmatter.
  - [x] MECHANICAL: plugin engine mirrors synced; `uv run goc validate` clean; full regression suite green.
worker: claude-code
---

# goc done closes cards whose created stamp was overwritten

## Problem

`goc new` stamps `created:` (and `draft: true`) and tells the agent to edit README.md. An agent
whose write tool needs no prior read tends to rewrite the file from scratch, re-typing the fields
it remembers; `created` and `draft` are the ones it forgets. None of the verbs that write a card
back looked at the field: `_cmd_done` checked the DoD, the human gate and the summary
(`summary_release_error`), but not the required fields `validate_card` enforces. The card closed
validate-red, and the deck stayed red until someone reconstructed the timestamp, a value nobody
should guess.

Seen in a consuming deck: four cards in ten days, each filed with `goc new --summary …` and
rewritten wholesale within seconds; two of them were then closed by `goc done` without a word.

Before the fix, in a throwaway deck: `goc new card-a --summary …`; overwrite README.md with the
same fields minus `created`/`draft`; `goc validate` → `card-a: created: required field missing`;
`goc done card-a` → exit 0, `status: done`; `goc validate` → still red.

## Fix

- `created_restore(card, card_dir)` (`goc/engine.py`) recovers a missing stamp from evidence: the
  card directory's birth time (`st_birthtime`; on Linux coreutils `stat -c %W`, because Python's
  `os.stat` does not expose statx there) and the author time of the commit that first added
  README.md (`git log --follow --diff-filter=A`). Both bound the filing time from above (a later
  checkout is born after the filing, a commit cannot predate its file), so the earlier one is
  kept. The current time is never written: it is not when the card was created.
- `publish`, `status` (every transition), `done` and `done --bundle` apply it before writing the
  card and print `<title>: created: restored <stamp> from <source>`. With no evidence they refuse
  with exit 2 and a message that rules out the clock; `done --bundle` refuses before closing any
  card.
- The `goc new` hint now reads "edit … in place … keep the generated frontmatter (created, draft)
  rather than rewriting the file".
- Out of scope: the other writers (`decide`, `wait`, `advance`, `move`, `attest`) do not restore;
  `validate` stays the net there, as it does for a card no verb touches after the rewrite.

## Verification

`tests/test_release_verbs_restore_a_lost_created_stamp.py`, six tests: commit evidence for
`publish`, `status active`, `status blocked`, `done` and the bundle (the commit is dated before
the directory's birth in the test checkout, so the earlier bound must win); birth time outside
git, with a one-second gap so a clock-based stamp would differ; refusal without evidence (a `stat`
that fails, no git); an intact stamp left alone; the new hint. On the unchanged engine 8 subtests
fail; picking the later bound instead of the earlier turns 5 red. Full suite: 1389 tests green.

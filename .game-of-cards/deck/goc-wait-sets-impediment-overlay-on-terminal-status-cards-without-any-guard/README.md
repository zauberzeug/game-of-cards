---
title: goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard
summary: "`goc wait` wrote `waiting_on` / `waiting_until` onto `done`, `disproved` and `superseded` cards, contradicting their closure while `goc validate` looked away (`validate_waiting_overlay` skips terminal cards). It now refuses every closed card, setters and `--clear` alike, through the new shared `_refuse_terminal_mutation` helper, so the validator's skip only sees overlays carried over from a card's live state. The refusal names the forward path that works, a new card plus a post-close amendment in the closed card's log.md, because `goc status <old> superseded --by <new>` is refused for every terminal card."
status: done
stage: null
contribution: medium
created: "2026-05-29T15:56:05Z"
closed_at: "2026-10-24T05:05:35Z"
human_gate: none
advances:
  - terminal-status-guard-missing-across-mutation-verbs
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] PROCESS: decision recorded in `## Decision required` — guard `goc wait` against terminal targets (the sibling-consistent option), allow with a "historical record" semantic, or split (allow `--clear` but reject `--reason`/`--until`). — decided 2026-10-22 via the parent epic: option 1, strict guard.
  - [x] TDD: `reproduce.py` exits zero (defect no longer fires) — running `goc wait` against a terminal card no longer mutates the overlay (or behaves per the recorded decision). — all 9 closed-card calls (3 terminal statuses × `--reason` setter, bare `--until`, `--clear`) exit 2 with the README byte-identical; it exited 1 on all 9 before the fix. `tests/test_terminal_status_guard.py` pins the same in CI.
  - [x] MECHANICAL: `_cmd_wait` in `goc/engine.py` refuses terminal targets through the parent epic's shared `_refuse_terminal_mutation` helper (decided 2026-10-22; `_cmd_decide` has stopped carrying a refusal to mirror), with an error message naming the replacement path (file a new card; supersede if the closed card needs revisiting). — the path named is the post-close amendment from `Skill(finish-card)` "After closure"; `goc status <old> superseded --by <new>` is refused for every terminal card, so the message does not offer it.
  - [x] PROCESS: `validate_waiting_overlay` (engine.py:2271) decision recorded — either keep the terminal skip (now defensible because the setter refuses) or extend it to emit a `TERMINAL_OVERLAY` warning for legacy stragglers. — decided 2026-10-22 via the parent epic: keep the terminal skip.
worker: {who: "claude[bot]", where: main}
---

# `goc wait` sets an impediment overlay on a terminal-status card without any guard

## Location

`goc/engine.py` — `_cmd_wait`, which wrote the overlay without reading
the card's status, and `validate_waiting_overlay`, whose terminal skip
kept the result out of `goc validate`.

## What was broken

`_cmd_wait` checked the reason enum and the date format, then set (or,
under `--clear`, dropped) `waiting_on` / `waiting_until` and rewrote the
README — with no `TERMINAL_STATUSES` check anywhere in the verb. A
`done`, `disproved` or `superseded` card took a fresh impediment overlay
that contradicted its closure, and `--clear` wiped an overlay the card
had carried into its closure. `_cmd_status` and `_cmd_done` already
refused terminal targets; `wait` was the member of the family that was
overlooked. (`_cmd_decide`, whose guard the filing compared against,
has since swapped its refusal for a terminal gate-repair path.)

`validate_waiting_overlay` skips terminal cards. That skip is
defensible only if the setter refuses to write the overlay in the first
place; before the fix the setter wrote it and the validator looked
away, so the contradiction was invisible to the one check meant to
catch it.

## Empirical evidence

First observed 2026-05-29 on `main`: `goc wait test-card --reason
external --until 2027-01-01` on a `disproved` card exited 0, the
frontmatter carried `status: disproved` beside `waiting_on: external`
and `waiting_until: 2027-01-01`, and `goc validate` printed
`OK  test-card`.

`reproduce.py` (this directory) is the canonical reproducer. It builds
a throwaway deck holding a `done`, a `disproved` and a `superseded`
card plus an open control, and runs `goc wait` three ways against each
closed card: the `--reason` setter, the bare `--until` setter, and
`--clear` over an overlay carried from the live state. On `main` before
the fix (2026-10-24) all nine calls exited 0 and rewrote the README.
After it, all nine exit 2 with the card byte-identical, and the control
still writes its overlay. Exit codes: 0 = defect no longer fires,
1 = defect fires, 2 = harness or precondition broken.

## Why it matters — reachability path

The overlay is the "can't *pull* yet" signal that
`pull-card`/`next-card`/`standup`/board-rendering all read. Terminal
cards are never pullable, so the overlay on a closed card is by
construction noise — but it persists in source control, ships to
consumers via `git pull`, and any downstream tool that reads the
overlay without re-checking status (the same shape that motivated
`board-paints-impediment-marker-on-terminal-cards-with-stale-overlay`)
will misbehave. That sibling fix preserved overlays that were *set
while the card was live* as a historical record; the present defect is
the inverse — overlays set *after* the card closed, which are not
history but contradiction.

Reachability: a session that closes a card and then runs `goc wait` on
it (typo, slug-collision, batch script, autonomous-loop misfire) is the
producing path. Per [board-paints-impediment-marker-on-terminal-cards-with-stale-overlay](../board-paints-impediment-marker-on-terminal-cards-with-stale-overlay/),
the closure verbs deliberately do NOT clear the overlay — so any later
`goc wait` call on the closed card is a write of fresh state that the
closure-as-historical-record contract does not endorse.

## Decision

*Resolved 2026-10-22T05:17:57Z:* Decided via parent terminal-status-guard-missing-across-mutation-verbs: option 1, strict terminal-status guard — goc wait refuses terminal targets for the setters and --clear alike; validate_waiting_overlay keeps its terminal skip

*Reasoning:* The maintainer approved the parent's recommended bundle in a human session on 2026-10-22, which resolves exactly this card's question; implement through the parent's shared _refuse_terminal_mutation helper, whose message is written fresh because _cmd_decide has stopped refusing terminal cards

## Fix

Applied 2026-10-24 per the decision:

- **Shared helper.** `_refuse_terminal_mutation(card, verb)` in
  `goc/engine.py` is the parent epic's one guard. A live card passes
  through. A `done` / `disproved` / `superseded` card gets a single
  message naming the card, its terminal status, the refusing verb and
  the forward path, then exit 2 before anything is written.
  `_cmd_wait` calls it right after `load_card_or_exit`, so the setters
  and `--clear` are refused alike. That includes a `--clear` with no
  overlay to remove: it used to print "nothing to do" and exit 0.
- **Forward path.** The message names the path that works on a closed
  card: file a new card and point to it from the closed card's log.md
  with a dated post-close amendment (`Skill(finish-card)` "After
  closure"). The fix sketch and the parent's agreed shape both proposed
  `goc status <old> superseded --by <new>`. `_cmd_status` refuses every
  terminal card ("terminal cards cannot be moved backward through
  `goc status`"), so a message naming it would send the user to a
  second refusal. `tests/test_terminal_status_guard.py` pins that
  premise; if closed-card supersession is ever allowed, the test fails
  and the message can name it again.
- **Validator.** `validate_waiting_overlay` keeps its terminal skip, as
  decided. Its docstring now records why that is sound: the only
  overlay goc leaves on a closed card is one carried over from its live
  state.
- **Help.** `goc wait --help` now says the verb acts on a live card's
  overlay.
- **Tests.** `tests/test_terminal_status_guard.py` covers the helper's
  contract (every live status passes; every terminal status exits 2
  with card, status, verb and forward path named). It also covers the
  CLI refusal for all three terminal statuses × three call shapes, and
  the open-card control. Run against the pre-fix engine it fails 16
  ways. Its CLI fixture already holds one card per terminal status, so
  `attest`, `quality-pass` and `move` can add their cases as they adopt
  the helper.

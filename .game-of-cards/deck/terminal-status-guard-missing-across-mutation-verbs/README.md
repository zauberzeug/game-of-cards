---
title: terminal-status-guard-missing-across-mutation-verbs
status: active
stage: null
contribution: medium
created: "2026-06-21T10:57:17Z"
closed_at: null
human_gate: none
advances: []
advanced_by:
  - goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard
  - goc-attest-mutates-log-md-on-already-closed-cards
  - goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards
  - goc-move-renames-terminal-status-cards-without-any-guard
tags: [epic, meta-fix, api-contract]
summary: "Aggregation epic for the family of mutation verbs that mutate cards whose `status` is already terminal (`done`/`disproved`/`superseded`) with no `TERMINAL_STATUSES` guard. `goc decide` got a guard (engine.py:~4557, via the closed sibling); `goc wait`, `goc attest`, `goc quality-pass`, and `goc move` still lack one. Collects the open siblings so they can be resolved with one shared guard shape (a helper applied across the verbs) instead of four independent point-fixes that drift."
definition_of_done: |
  - [ ] PROCESS: A shared guard shape is decided — either a reusable `TERMINAL_STATUSES` helper that each verb calls, or a per-verb inline check mirroring `_cmd_decide` (engine.py:~4557). Recorded in this card's log.md.
  - [ ] PROCESS: All four open child cards (`goc-wait-...`, `goc-attest-...`, `goc-quality-pass-...`, `goc-move-...`) are closed or superseded under the agreed shape; this epic's `advanced_by` roster all terminal.
  - [ ] MECHANICAL: Each guarded verb's error message names the supersede workflow (`goc status <old> superseded --by <new>`) where that is the correct forward path, matching the post-fix `_cmd_decide` message.
  - [ ] TDD: A regression test asserts each of the four verbs refuses a terminal-status target (exit non-zero, no mutation written).
  - [ ] PROCESS: Sibling-shape audit closed out — `_cmd_advance` / `_cmd_unadvance` (engine.py:~4383/4404) explicitly classified as in-scope (need a guard) or out-of-scope (supersession edges legitimately mutate closed cards), with the verdict recorded.
worker: {who: "claude[bot]", where: main}
---

# terminal-status-guard-missing-across-mutation-verbs

## What this epic coordinates

A family of `goc` mutation verbs share one root-cause defect: they
mutate a card whose `status` is already terminal (`done`,
`disproved`, `superseded`) with **no `TERMINAL_STATUSES` guard**, so a
closed card — the deck's durable record-axis artefact — silently gains
fresh state long after closure. `goc decide` was given the canonical
guard (`engine.py:~4557`); the rest of the family was overlooked when
that guard was added.

## Family roster

Open children (wired via `advanced_by`):

- [goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/) — `_cmd_wait` attaches a `waiting_on` / `waiting_until` overlay to terminal cards.
- [goc-attest-mutates-log-md-on-already-closed-cards](../goc-attest-mutates-log-md-on-already-closed-cards/) — `goc attest` rewrites `log.md` on already-closed cards.
- [goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards](../goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards/) — `goc quality-pass` rewrites `summary` / DoD on terminal cards.
- [goc-move-renames-terminal-status-cards-without-any-guard](../goc-move-renames-terminal-status-cards-without-any-guard/) — `goc move` retitles a closed card and rewrites historical backrefs.

Closed predecessor (record axis, not wired to avoid mutating a closed
card): `goc-decide-accepts-decisions-on-already-closed-cards` — the
card that added the canonical `_cmd_decide` guard the others should
mirror.

Related but distinct shape (not a child): `no-verb-can-fix-a-closed-at-that-contradicts-the-cards-status`
is about the *absence* of a repair verb for an already-broken
`closed_at`, not a missing guard on an existing mutation verb.

## Why it matters

A closed card is the kanban system's durable artefact: its slug,
directory name, backrefs, and `log.md` are what the deck-as-record
axis depends on. Each verb that mutates a terminal card without a
guard erodes that axis in a different way — a stale impediment
overlay, a post-close `log.md` edit, a silently rewritten DoD, a
retitle that breaks every existing pointer. Fixing them one at a time
re-derives the same guard four times and lets the shape drift between
verbs; this epic exists so the family is resolved under one decision
about the shared guard shape.

This card was surfaced by a `refine-deck` orphaned-dependency pass:
the four siblings cross-referenced each other in prose
(`goc-move`'s body explicitly proposes this umbrella) but carried no
schema edges, so the family was invisible to the scheduler. It closes
when its `advanced_by` roster is terminal.

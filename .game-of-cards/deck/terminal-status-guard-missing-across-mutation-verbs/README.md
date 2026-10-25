---
title: terminal-status-guard-missing-across-mutation-verbs
status: open
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
summary: "Aggregation epic for the family of mutation verbs that mutate cards whose `status` is already terminal (`done`/`disproved`/`superseded`) with no `TERMINAL_STATUSES` guard: `goc wait`, `goc attest`, `goc quality-pass` and `goc move`. Decided 2026-10-22: one shared helper that strictly refuses terminal targets, `goc move --force` as the only escape hatch, advance/unadvance out of scope, and a freshly written message — `goc decide`'s old guard became a terminal gate-repair path, so there is nothing to mirror. The helper, `_refuse_terminal_mutation`, landed 2026-10-24 with `goc wait` and `goc attest` adopted it 2026-10-25; `quality-pass` and `move` still need to."
definition_of_done: |
  - [x] PROCESS: A shared guard shape is decided — either a reusable `TERMINAL_STATUSES` helper that each verb calls, or a per-verb inline check mirroring `_cmd_decide` (engine.py:~5868). Recorded in this card's log.md. — decided 2026-10-22: one reusable helper (see "## Agreed shape").
  - [ ] PROCESS: All four open child cards (`goc-wait-...`, `goc-attest-...`, `goc-quality-pass-...`, `goc-move-...`) are closed or superseded under the agreed shape; this epic's `advanced_by` roster all terminal.
  - [ ] MECHANICAL: Each guarded verb's error message names the card, its terminal status and the supersede workflow (`goc status <old> superseded --by <new>`) where that is the correct forward path. The message is written fresh in the shared helper: `_cmd_decide` has stopped refusing terminal cards (it runs a terminal gate-repair path, engine.py `_cmd_decide`), so there is no message to mirror. — 2026-10-24: that command is the correct path for no terminal card (`_cmd_status` refuses them all), so the helper names the `Skill(finish-card)` "After closure" path instead; met for `wait` and `attest`.
  - [ ] TDD: A regression test asserts each of the four verbs refuses a terminal-status target (exit non-zero, no mutation written). — 2026-10-25: `wait` and `attest` covered in `tests/test_terminal_status_guard.py`; `quality-pass` and `move` remain.
  - [x] PROCESS: Sibling-shape audit closed out — `_cmd_advance` / `_cmd_unadvance` (engine.py:~5662/4404) explicitly classified as in-scope (need a guard) or out-of-scope (supersession edges legitimately mutate closed cards), with the verdict recorded. — out of scope, recorded in the 2026-10-22 decision: edge maintenance on a terminal endpoint is part of the record axis.
worker: {who: "claude[bot]", where: main}
---

# terminal-status-guard-missing-across-mutation-verbs

## What this epic coordinates

A family of `goc` mutation verbs share one root-cause defect: they
mutate a card whose `status` is already terminal (`done`,
`disproved`, `superseded`) with **no `TERMINAL_STATUSES` guard**, so a
closed card — the deck's durable record-axis artefact — silently gains
fresh state long after closure. `goc decide` was once given a guard;
the rest of the family was overlooked when it was added, and `goc
decide` itself has since replaced the guard with a terminal gate-repair
path (`_cmd_decide`), so none of the four has a sibling to copy.

## Family roster

Children (wired via `advanced_by`):

- [goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/) — `_cmd_wait` attached a `waiting_on` / `waiting_until` overlay to terminal cards. **Closed 2026-10-24**: introduced the shared helper and the `tests/test_terminal_status_guard.py` fixture the other three extend.
- [goc-attest-mutates-log-md-on-already-closed-cards](../goc-attest-mutates-log-md-on-already-closed-cards/) — `goc attest` appended a fresh `## Closure verification` block to a closed card's `log.md`. **Closed 2026-10-25**: `_cmd_attest` calls the helper before loading the check config. The fixture now turns auto-commit off in its scratch `config.yaml` instead of passing `--no-commit` on every call, which `attest` — like `move` and `quality-pass` — does not accept.
- [goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards](../goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards/) — `goc quality-pass` rewrites `summary` / DoD on terminal cards.
- [goc-move-renames-terminal-status-cards-without-any-guard](../goc-move-renames-terminal-status-cards-without-any-guard/) — `goc move` retitles a closed card and rewrites historical backrefs.

Closed predecessor (record axis, not wired to avoid mutating a closed
card): `goc-decide-accepts-decisions-on-already-closed-cards` — the
card that added the original `_cmd_decide` guard, since replaced by
decide's terminal gate-repair path.

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

## Decision

*Resolved 2026-10-22T05:17:11Z:* Approve the recommended bundle: strict refuse via one shared terminal-status helper across wait, attest, move, quality-pass and the summary/DoD rewrites; goc move gets a --force escape hatch; advance/unadvance stay out of scope; the helper's message is written fresh

*Reasoning:* The maintainer approved the bundle in a human session on 2026-10-22; it is the sibling-consistent 'closed cards are read-only' default, and _cmd_decide has stopped refusing terminal cards (it now runs a terminal gate-repair path), so there is no refusal message left to mirror

## Agreed shape

The approved bundle (the full option catalogue is archived in
`log.md`; each child carries its own "Decided via parent" record):

1. **One helper.** `_refuse_terminal_mutation(card, verb)` in
   `engine.py` (landed 2026-10-24 with `goc wait`), called right after
   `load_card_or_exit` in every guarded verb. It prints a fresh
   message naming the card, its terminal status, the verb and the
   forward path, then exits 2 without writing anything. The forward
   path is `Skill(finish-card)` "After closure": file a new card and
   point to it from the closed card's log.md. The bundle originally
   named `goc status <old> superseded --by <new>`, but `_cmd_status`
   refuses every terminal card, so that path is open to no card this
   guard stops. The `replacement="supersede"` keyword went with it.
   `goc move` will need a `--force` hint in its refusal; add it to the
   helper rather than inlining a second message.
2. **`goc wait`** → strict refuse, setters and `--clear` alike.
   `validate_waiting_overlay`'s terminal skip stays: a terminal overlay
   can then only be inherited from the live state before closure.
3. **`goc attest`** → strict refuse at the top of `_cmd_attest` (landed 2026-10-25).
4. **`goc quality-pass`** → filter terminal cards out of the Layer-2
   LLM sample regardless of `--status` (Layer 1 still reports over them,
   read-only), and guard `_apply_summary_rewrite` / `_apply_dod_rewrite`
   so every future caller inherits the protection.
5. **`goc move`** → reject by default, `--force` to bypass (the
   `goc done --force` precedent). The quality-pass `move` subprocess
   inherits the rejection through the non-zero exit code.
6. **`_cmd_advance` / `_cmd_unadvance`** → out of scope; supersession
   legitimately maintains edges on closed cards.


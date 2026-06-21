---
title: terminal-status-guard-missing-across-mutation-verbs
status: active
stage: null
contribution: medium
created: "2026-06-21T10:57:17Z"
closed_at: null
human_gate: decision
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

## Decision required

The four open children each carry their own `human_gate: decision`
with a menu of options. This epic exists so the family is resolved
under **one** shared decision instead of four that can drift. An
autonomous `pull-card` session consolidated the children's
recommendations into the single bundle below; the per-verb option
catalogues remain in each child's body. Approving this bundle (via
`Skill(decide-card)` on this epic) lowers the gate and authorises a
follow-up session to implement all four verbs + the shared helper in
one commit-series, then close the children under the chosen shape.

The recommendation everywhere is the **sibling-consistent strict
guard** — every other state-touching verb (`done`, `status`, `decide`)
already refuses terminal targets; the deck convention "closed cards
are read-only for state-touching verbs" is the established axis. The
genuine taste calls are the `goc move` escape hatch and the
`validate_waiting_overlay` follow-through; both are called out below.

### Recommended bundle

1. **Shared shape — one helper, not four inline checks.** Add
   `_refuse_terminal_mutation(card, verb, *, replacement="supersede")`
   to `engine.py` that prints an error mirroring the post-fix
   `_cmd_decide` message (names the card, its terminal status, and the
   `goc status <old> superseded --by <new>` forward path) and
   `sys.exit(2)`. Each guarded verb calls it immediately after
   `load_card_or_exit`. With five call-sites (decide already inline +
   four new) the helper is past the "two sites is too small" threshold
   the closed predecessor's DoD flagged. (`_cmd_decide` may stay inline
   or be refactored onto the helper — implementer's choice, since its
   message is the template.)

2. **`goc wait`** → strict refuse (child option 1). On a terminal
   target, exit non-zero, write nothing. Leave
   `validate_waiting_overlay`'s terminal-skip as-is — it becomes
   *defensible* once the setter refuses, because a terminal overlay can
   then only be inherited from a pre-closure live state (history),
   never freshly created. No `TERMINAL_OVERLAY` warning needed.

3. **`goc attest`** → strict refuse (child option 1). Guard at the top
   of `_cmd_attest`; the misleading `Next: goc done …` print is then
   unreachable on the terminal path.

4. **`goc quality-pass`** → filter **+** helper-guard (child
   recommendation "(a)+(c)"). Filter terminal cards out of the Layer-2
   LLM *sample* regardless of `--status` (Layer-1 antipattern scan still
   reports over them, read-only), AND guard `_apply_summary_rewrite` /
   `_apply_dod_rewrite` so any future caller inherits the protection.

5. **`goc move`** → reject-by-default **with a `--force` escape hatch**
   (child option c). The record axis defaults to immutability; a
   deliberate closed-card retitle (slug-normalization sweep) is rare
   enough that an explicit per-call `--force` is the right ergonomic,
   matching the `goc done --force` precedent. The quality-pass `move`
   subprocess hop inherits the rejection via the non-zero exit code (no
   `--force` passed), which is the intended behaviour.

6. **`_cmd_advance` / `_cmd_unadvance`** → **out of scope (no guard).**
   These maintain `advances`/`advanced_by` edges, and the supersession
   sibling (`goc status … superseded --by`) legitimately mutates a
   closed card's relationship edges as part of the record axis. Edge
   maintenance on a terminal endpoint is a feature, not the defect this
   family targets. Record this classification in `log.md` to close DoD
   item 5.

### If you disagree

The reversible alternative on the one real taste call: drop the
`--force` hatch on `goc move` (child option a, plain reject) if a
closed-card retitle should never be possible without re-opening the
question per-card. Everything else in the bundle is the conservative,
convention-aligned default; diverging from it would re-open the
"closed cards are read-only" axis the deck already settled.

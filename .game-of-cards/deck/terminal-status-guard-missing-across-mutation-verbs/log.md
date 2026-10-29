## 2026-06-21: claimed and gate raised to `decision`

An autonomous `pull-card` session pulled this epic (`human_gate: none`,
the only ready card) and discovered its completion depends on resolving
four children that each carry `human_gate: decision`
(`goc-wait-...`, `goc-attest-...`, `goc-quality-pass-...`,
`goc-move-...`). The guard *shape* per verb — notably the `goc move`
`--force` escape hatch and the `quality-pass` filter-vs-error choice —
is a genuine API-contract taste call, and this repo defines no
project-local `pull-card` consultation hook. Per the pull-card Andon
protocol (no hook → surface the decision), the session did the work it
*could* do autonomously: consolidated the four scattered per-verb
option menus into one coherent recommended bundle (the
`## Decision required` section), then raised this epic's gate so the
human approves the family in a single `Skill(decide-card)` action
rather than four.

The recommended bundle: a shared `_refuse_terminal_mutation` helper
(five call-sites now justify it); strict refuse for `wait` and
`attest`; filter+helper-guard for `quality-pass`; reject-with-`--force`
for `move`; and `_cmd_advance`/`_cmd_unadvance` classified **out of
scope** (supersession edges legitimately mutate closed-card
relationships — that pre-answers DoD item 5). No code changed this
session; implementation waits on the decision.

## 2026-07-09T05:30:00Z — Sibling-shape precedent

[`path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck`](../path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck/)
closed by introducing `resolve_card_dir()` — a single shared helper that every
title-taking verb routes through — rather than per-verb inline checks. That is
a working precedent for this epic's "reusable helper that each verb calls"
option in the PROCESS DoD item, and the helper itself (called at the top of
each verb's title resolution) is a candidate hang-point for a shared
terminal-status guard.

## 2026-06-21T10:57:17Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

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


## 2026-10-22T05:17:11Z: decision recorded

Approve the recommended bundle: strict refuse via one shared terminal-status helper across wait, attest, move, quality-pass and the summary/DoD rewrites; goc move gets a --force escape hatch; advance/unadvance stay out of scope; the helper's message is written fresh — The maintainer approved the bundle in a human session on 2026-10-22; it is the sibling-consistent 'closed cards are read-only' default, and _cmd_decide no longer refuses terminal cards (it now runs a terminal gate-repair path), so there is no refusal message left to mirror. Gate decision → none. Status active → open — the claim parked behind the gate is released, so the next pull-card claims the card per this decision.

## 2026-10-24T05:03:39Z — Shared helper landed with `goc wait`; forward path corrected

[`goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard`](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/)
introduced `_refuse_terminal_mutation(card, verb)` in `goc/engine.py` and
closed. Two departures from the approved bundle, both forced by evidence
rather than taste:

- **Forward path.** The bundle had the helper name
  `goc status <old> superseded --by <new>`. Run against a `done` card,
  that command exits 2 with "terminal cards cannot be moved backward
  through `goc status`" — `_cmd_status` refuses every terminal card, so a
  message naming it sends the user from one refusal to another. The
  helper instead names the path `Skill(finish-card)` "After closure"
  documents: file a new card and point to it from the closed card's
  log.md with a dated post-close amendment.
  `tests/test_terminal_status_guard.py` pins the premise, so the message
  can name supersession again if closed-card supersession ever becomes
  legal.
- **Signature.** With no supersede path to choose, the
  `replacement="supersede"` keyword had nothing to select, so the helper
  takes `(card, verb)`. `goc move` will need a `--force` hint in its
  refusal; that belongs in the helper, not a second inline message.

The README's "Agreed shape" item 1 and the MECHANICAL DoD item now carry
this. `tests/test_terminal_status_guard.py` already holds one fixture
card per terminal status, so `attest`, `quality-pass` and `move` can add
their cases there as they adopt the helper.

## 2026-10-25T04:35:08Z — `goc attest` adopted the helper

[`goc-attest-mutates-log-md-on-already-closed-cards`](../goc-attest-mutates-log-md-on-already-closed-cards/)
closed: `_cmd_attest` calls `_refuse_terminal_mutation(card, "attest")`
right after `load_card_or_exit`, ahead of the empty-config and all-skipped
refusals, so a closed card is refused for being closed rather than for
whatever its config happens to lack.

One fixture change the remaining children inherit. `_goc` in
`tests/test_terminal_status_guard.py` used to append `--no-commit` to
every call, but only the commit-capable verbs take that flag — `attest`,
`move` and `quality-pass` exit 2 on it as an unknown argument, which would
have satisfied the exit-code assertion for the wrong reason. The scratch
deck now carries a `config.yaml` with `workflow.auto_commit: false`, and
with layer-3 checks every probe card passes, so an unguarded verb visibly
writes and exits 0 instead of failing on something unrelated. `move` and
`quality-pass` can call `_assert_refused` without per-verb flags.

## 2026-10-25T04:52:07Z — `goc quality-pass` adopted the helper

[`goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards`](../goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards/)
closed in the decided (a) + (c) shape. `_cmd_quality_pass` leaves closed
cards out of the Layer-2 sample whatever `--status` selected, and makes no
LLM call when every selected card is closed. Layer 1 still reports on them.
`_apply_summary_rewrite` and `_apply_dod_rewrite` call
`_refuse_terminal_mutation` before writing.

One refinement over the bundle: the helpers guard a fresh
`load_card_or_exit(card.path, card.title)`, not the `Card` they are handed.
Quality-pass loads its sample before the LLM call and the accept/reject
prompts, so a card a parallel session closes in that window still reads as
live in the caller's copy. With the sample filter in place, that window is
the only way a closed card reaches the helpers today.

Only `goc move` remains. Its child confirmed on 2026-10-25 that
`goc move done-card renamed-done-card` still renames a `done` card with
exit 0. `_goc` in `tests/test_terminal_status_guard.py` now accepts
`extra_env`, and `_snapshot(title)` returns a card directory's bytes for the
before/after comparisons. `move` can use `_assert_refused` as it is, plus
one `--force` case.

## 2026-10-29T04:42:16Z — `goc move` adopted the helper

[`goc-move-renames-terminal-status-cards-without-any-guard`](../goc-move-renames-terminal-status-cards-without-any-guard/)
closed in the decided (c) shape (commit 79ed3f73). `_cmd_move` resolves the
source card first. Unless `--force` is passed, it calls
`_refuse_terminal_mutation(..., "move", override="--force")`. The call sits
ahead of the checks on the new title, which no title could get a closed card
past, and ahead of `--dry-run`, so the preview never lists a rename the real
run would refuse.

The `--force` hint is the helper's new keyword-only `override`, so it is
part of the one shared message rather than a second, inline one. Verbs that
pass none are told of no flag they lack. `_apply_verdict_interactive` needed
no change: its `goc move` subprocess never passes `--force`. A test pins
that path by closing a card while a fake `claude` is mid-call.

`_assert_refused` in `tests/test_terminal_status_guard.py` now snapshots
the whole deck rather than the one card, because a move rewrites other
cards' references too. `wait` and `attest` pass under the stricter
comparison unchanged.

## 2026-10-29T04:42:16Z — Closure

- **What changed**: no code of its own — the epic closes because its `advanced_by` roster is terminal: `goc wait` (2026-10-24, cf74ab76), `goc attest` (2026-10-25, 07427d22), `goc quality-pass` (2026-10-25, 7aaecd36) and `goc move` (2026-10-29, 79ed3f73) all refuse a closed card through `_refuse_terminal_mutation` (`goc/engine.py:5631`), in the shapes recorded under "## Agreed shape". `advance` / `unadvance` stay out of scope by the 2026-10-22 decision.
- **Verification**: `tests/test_terminal_status_guard.py` covers all four verbs (17 tests). The four children's reproducers each exit 0 on the current engine.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1416 passed / 0 failed / 0 xfailed; `goc validate` exit 0

## Closure verification (2026-10-29T04:42:24Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 4 closed
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-29 — Closure' present

## 2026-07-01T02:45:00Z — Second instance connected

Wired [`waiting-filter-surfaces-draft-scaffolds-as-active-impediments`](../waiting-filter-surfaces-draft-scaffolds-as-active-impediments/)
(done) into `advanced_by`. It is a second drift of this exact rule at
the same `--waiting` call site: the hand-inlined gate copied only the
terminal-status half of the board's `card_cell` gate and dropped the
`card_is_draft` half, so draft scaffolds with an overlay leaked into
`--waiting`. Fixed there by adding `and not card_is_draft(t)`.

This widens the meta-fix scope: the live "shows `⏳`" variant of the
centralized helper must exclude `card_is_draft` in addition to
terminal-status, or `--waiting` / `card_cell` will still hand-inline the
draft clause and can drift a third time. Updated the summary, the
"## Why it matters" section, and the MECHANICAL/TDD DoD items to record
the draft axis. No decision made — the card stays parked at
`human_gate: decision` pending the helper-shape choice.

## 2026-09-16T05:05:53Z — New instance wired: a caller outside Python

Commit 6e021a5d (closing
`standup-impeded-section-omits-active-cards-carrying-a-waiting-overlay`)
added a seventh hand-inlined copy of this liveness gate, now wired as an
`advanced_by` instance. The README caller table and the new
"A caller no helper can reach" section carry the detail.

Why it is worth a journal entry rather than just a table row: every
caller listed before it is a Python call site inside `goc/engine.py`,
so Option A and Option B both retire it by construction. This one is a
shell pipeline in a skill body that runs with no installed package and
cannot import the engine at all, so no helper shape reaches it. The
SessionStart hook is a second non-importer of the same kind. The open
question the decision should now also answer is whether those surfaces
are in scope, and if so whether the rule for them is "call
`goc --waiting --json`" rather than "re-derive from the JSON payload".

No status or gate change — the helper shape is still the human's call.

## 2026-11-09T01:59:02Z — Staleness re-check

As-filed anchors gone from HEAD: `engine.py:2982` (`not_ready = live and (`), moved by `e861360e`
(the board gate became `not_ready = live and not is_draft and (`).
Reproducer: none.
Verdict: not verified (no reproducer) — needs a human re-read. Reading HEAD: a `live_impeded` helper (added in `fd34c7cc`) now owns the live variant and the `--waiting` filter routes through it, so the table's `--waiting` row is out of date; board `card_cell`, `card_is_workable_for_scheduler`, `card_is_ready` and the gated-leverage line still inline the gate.
Re-anchored `engine.py:2982-2986` → `:4141-4145` (board `card_cell`'s `not_ready`).
Gate unchanged.

## 2026-11-09T04:39:42Z — Another copy of the live variant, outside the overlay callers

[cascade-root-warning-counts-only-cards-in-the-retired-blocked-status](../cascade-root-warning-counts-only-cards-in-the-retired-blocked-status/)
retargeted the CASCADE_CHAIN_ROOT walk from `status: blocked` to live
cards. It added a local `live()` in `validate_blocker_coherence`, the
live variant without the overlay, because no bare live predicate exists
to call. The README now lists it after the caller table. The table stays
scoped to `waiting_impedes` callers. This site belongs to the same rule,
so the helper decision should say whether a bare live predicate is part
of it.

No status or gate change.

## 2026-11-23T02:30:00Z — Two caller rows rewritten: the standup copy is retired, `--waiting` calls the helper

The 2026-11-23 refine-deck citation pass declined
`goc/templates/skills/standup/SKILL.md:22` as `anchor text absent`: the
hand-typed gate the table quoted is gone from the template. Since `6291964e`
(2026-10-22) the Section 2 block runs `goc --waiting -v`, so it inherits the
engine's `live_impeded` — the delegate-to-the-CLI route `## A caller no
helper can reach` proposed for non-importers.
`standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits` closed
on the same evidence that day.

The 2026-11-09 re-check already noted that the `--waiting` row was out of
date; the filter calls `live_impeded(t, include_drafts=include_drafts)`
(`goc/engine.py:5064`), as does `format_waiting_overlay` (`:3435`). Both rows
and the "No single function owns the rule" sentence are rewritten in place;
`## A caller no helper can reach` keeps its argument under a note.

Still inlined at HEAD: board `card_cell`'s `not_ready`, `card_is_ready`,
`card_is_workable_for_scheduler`, the gated-leverage line, and the local
`live()` in `validate_blocker_coherence`. The SessionStart hook is the
remaining non-importer. The decision is unchanged in substance; its scope is
one copy smaller. Gate unchanged.

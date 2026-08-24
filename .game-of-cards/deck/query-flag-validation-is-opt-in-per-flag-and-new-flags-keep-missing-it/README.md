---
title: query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it
summary: "Query-flag validation is bolted on one flag at a time (--tag, --status, --since each got their own guard card), so every unguarded flag silently returns wrong or empty output with exit 0: --advances/--advanced-by accept nonexistent titles, and --closed-since composes with a non-terminal --status or with --waiting into can-never-match queries. Instance 2 (--board overriding --json) has since been guarded one-off, which is the family shape repeating rather than the fix. Meta-fix: one declared contract per query flag, enforced centrally, so a new flag without a contract fails closed."
status: open
stage: null
contribution: medium
created: "2026-07-11T01:24:14Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - invalid-status-filter-silently-empties-queue
  - invalid-tag-filter-silently-empties-queue
  - invalid-since-date-silently-empties-done-query
  - done-shortcut-overrides-status-filter
  - since-filter-without-done-hides-open-queue
  - empty-queue-view-prints-nothing-instead-of-saying-no-cards-match
  - empty-result-line-reports-a-drained-ready-queue-that-still-has-cards
  - empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card
  - zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface
  - zero-match-line-omits-hidden-drafts-whenever-the-status-filter-is-all
  - board-flag-silently-overrides-json-and-returns-an-ascii-table
tags: [bug, meta-fix, api-contract]
definition_of_done: |
  - [ ] PROCESS: mechanism decision recorded (option A/B/C below, plus error-vs-warn for unknown edge-filter titles) and gate lowered to none
  - [ ] TDD: reproduce.py exits zero — all five probes either hard-error or emit a diagnostic naming the offending flag/value
  - [ ] TDD: regression tests cover unknown --advances/--advanced-by title, --json + --board conflict, non-terminal --status + --closed-since, and --waiting + --closed-since
  - [ ] MECHANICAL: the instance table in this README is re-audited after the fix and every row reads "guarded"
  - [ ] PROCESS: a guard makes future query flags fail closed — adding a parser flag without a declared validation/conflict contract turns the suite red
---

# Query-flag validation is opt-in per flag, and new flags keep missing it

`goc`'s default (no-subcommand) query surface validates its flag inputs
and flag compositions one flag at a time. Five closed cards each added
one guard; every flag that never got its own card still resolves invalid
input or a contradictory composition silently — empty or wrong-format
output, exit 0.

## Location

- `goc/engine.py:2959` — `filter_cards` `--advances` / `--advanced-by`
  membership tests (no existence check on the queried title)
- `goc/engine.py:4263` — `_cmd_default` presentation dispatch
  (`if args.board: ... elif args.as_json: ...`)
- `goc/engine.py:4180` — status auto-extend for `--waiting` /
  `--closed-since` fires only when `--status` is unset; nothing checks
  the explicit-status or `--waiting`+`--closed-since` compositions

## What's broken

Three instances, confirmed on this deck (2026-07-11). Two are still
unguarded; instance 2 was fixed one-off on 2026-08-18 (see below):

**1. `--advances` / `--advanced-by` accept a nonexistent card title.**
`filter_cards` (`goc/engine.py:2959`) tests membership only:

```python
if advances:
    out = [
        t
        for t in out
        if isinstance(t.frontmatter.get("advances"), list)
        and advances in t.frontmatter["advances"]
    ]
```

The queried title is never checked against `by_title` (already threaded
into `filter_cards` for the `ready` branch). A typo'd or since-renamed
title yields "no results", indistinguishable from "no edges". Contrast
`validate_tag_filters` (`goc/engine.py:3102`), which exits 2 with a
remedy for an unknown tag — and `compute_values`, which stderr-WARNs on
dangling `advances` edges in card frontmatter while the CLI filter for
the same edge field stays silent.

**2. `--board` silently overrides `--json` — GUARDED 2026-08-18, one-off.**
The presentation dispatch (`goc/engine.py:4263`) was
`if args.board: ... elif args.as_json: ...`, so `goc --json --board`
printed the ASCII kanban grid with exit 0 — a machine consumer expecting
JSON got unparseable output. Fixed by
[board-flag-silently-overrides-json-and-returns-an-ascii-table](../board-flag-silently-overrides-json-and-returns-an-ascii-table/)
(done, 2026-08-18), which added exactly the guard this row's precedent
predicted: a hand-written per-pair conflict check at
`goc/engine.py:4096-4107`, spelled like
`goc: error: pass only one of --done / --status` (exit 2,
`goc/engine.py:4160`).

**That fix is evidence for this card, not a dent in it.** It was found by
an independent audit pass that did not reach this card during dedup — the
root card's title names neither flag — and it shipped the 6th
hand-written per-instance guard on a surface whose problem is that the
guards are per-instance. This card's DoD item 5 (a guard that makes future
query flags fail closed) is the only item that would have prevented it,
and nothing about the one-off fix moves it. Two rows below remain
unguarded and the mechanism decision is still open.

Same-site symptom, still unaddressed: `--slim` is read only inside the
`elif args.as_json` branch, so `goc --slim` without `--json` is a silent
no-op (its help text does say "With --json:", so that one is at least
documented). `--max-rows` has the same shape against `--board`.

**3. `--closed-since` composes into can-never-match queries.** The
status auto-extend (`goc/engine.py:4180`) fires only when
`args.status_flag is None`. With an explicit non-terminal status,
`goc --status open --closed-since 7d` requires `closed_at` set on an
open card — a state `goc validate` itself flags as incoherent — and
`goc --waiting --closed-since 24h` requires non-terminal ∧ closed.
Both print zero result rows with exit 0 on a deck that has both
impeded cards and recent closures.

## Empirical evidence

`uv run python .game-of-cards/deck/query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it/reproduce.py`:

```
[FAIL (silent, exit 0)] goc --advances no-such-card-xyz-reproduce
         exit=0  stdout[0]='ACTIVE: 5 claimed cards outside this open queue: support-external-game'
[FAIL (silent, exit 0)] goc --advanced-by no-such-card-xyz-reproduce
         exit=0  stdout[0]='ACTIVE: 5 claimed cards outside this open queue: support-external-game'
[OK  (guarded)] goc --json --board
[FAIL (silent, exit 0)] goc --status open --closed-since 7d
         exit=0  stdout[0]='ACTIVE: 5 claimed cards outside this open queue: support-external-game'
[FAIL (silent, exit 0)] goc --waiting --closed-since 24h
         exit=0  stdout[0]='No cards match (status: all; waiting: active impediment overlay; close'

contrast (per-flag guards that DO exist):
  goc --tag no-such-tag           -> exit=2 stderr="goc: error: --tag: unknown tag 'no-such-tag' — add a project"
  goc --done --status open        -> exit=2 stderr='goc: error: pass only one of --done / --status'

DEFECT: 4/5 query-flag probes silently return wrong/empty output with exit 0
```

Re-run 2026-08-18. The `--json --board` probe flipped to `[OK (guarded)]`
after instance 2 was fixed one-off; the `--waiting --closed-since` probe
now prints a zero-match sentence instead of nothing, courtesy of
[empty-queue-view-prints-nothing-instead-of-saying-no-cards-match](../empty-queue-view-prints-nothing-instead-of-saying-no-cards-match/)
— legible, still a query that can never match. The remaining 4 are the
ones this card's DoD covers.

## Why it matters — this is the 6th–8th instance of one root-cause shape

The family is already catalogued, one card per flag, all closed:

| Instance | Card | Guard shape shipped |
|---|---|---|
| unknown `--status` value | [invalid-status-filter-silently-empties-queue](../invalid-status-filter-silently-empties-queue/) | argparse `choices` |
| unknown `--tag` value | [invalid-tag-filter-silently-empties-queue](../invalid-tag-filter-silently-empties-queue/) | `validate_tag_filters`, exit 2 |
| malformed `--since` date | [invalid-since-date-silently-empties-done-query](../invalid-since-date-silently-empties-done-query/) | `parse_since_filter`, exit 2 |
| `--done` ∧ `--status` conflict | [done-shortcut-overrides-status-filter](../done-shortcut-overrides-status-filter/) | explicit conflict error, exit 2 |
| `--since` without `--done` | [since-filter-without-done-hides-open-queue](../since-filter-without-done-hides-open-queue/) | explicit conflict error, exit 2 |
| unknown `--advances`/`--advanced-by` title | this card, instance 1 | **none** |
| `--json` ∧ `--board` conflict | [board-flag-silently-overrides-json-and-returns-an-ascii-table](../board-flag-silently-overrides-json-and-returns-an-ascii-table/) | explicit conflict error, exit 2 — the 6th hand-written one |
| `--closed-since` ∧ non-terminal status / `--waiting` | this card, instance 3 | **none** |
| draft exclusion — a conjunct with *no flag* | [empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card](../empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card/) | output-half clause, count-gated |
| that clause over-counting under `--waiting` / `--closed-since` | [zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface](../zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/) | recount replays all three query stages |
| that clause silenced by `--status all` (incl. the value `--waiting` auto-resolves to) | [zero-match-line-omits-hidden-drafts-whenever-the-status-filter-is-all](../zero-match-line-omits-hidden-drafts-whenever-the-status-filter-is-all/) | recount's `status` guard deleted |

The last three rows are one flag's worth of clause needing three cards,
which is the family shape at its sharpest: the draft conjunct has no flag
of its own, so the output half is all it ever gets — and that output half
then had to be corrected twice more, once for over-counting and once for
being silenced entirely. The third one is the tell for the mechanism
question below: its guard was keyed to `--status`, a *different* flag,
and read correctly for one of the three stages the query runs. A per-flag
table cannot express "this clause is a claim about the whole predicate",
which is why the same clause keeps being wrong in a new way each time.

Each fix so far guarded exactly the flag its card named, and the next
flag added to the parser (`--advances`/`--advanced-by`, `--board`,
`--closed-since`, `--waiting`) shipped with no guard. Per the audit
sibling-sweep rule, the 4th+ instance of a catalogued family files the
architectural meta-fix, not three more instance cards.

The `--board` row updated on 2026-08-18 is the family's clearest
demonstration to date, because it happened *after* this card was filed:
an independent audit pass rediscovered instance 2 from scratch, filed it,
and shipped a sixth hand-written per-pair guard — without ever reaching
this card, whose title names no flag. So the table now records six
one-off guards and two unguarded rows, which is the same ratio it
described at filing time with one more guard in it. Only DoD item 5 (a
fail-closed contract for *future* flags) changes that trajectory.

Reachability: all probes are plain CLI invocations of the default query
verb — the exact commands scripted consumers (CI dashboards, the
autonomous-loop skills, `goc --json` pipelines) already run. The
`--json --board` case corrupts a machine-read surface; the others
return "nothing matched" for queries that could never match anything.

### One flag can never have an input-side contract

`--worker` is a constraint on whatever mechanism the decision below
picks: `worker` values are deliberately unregistered (AGENTS.md §
"Card authoring rules" — "The value is unregistered — use a person
slug, a machine name, or a capability tag"), so there is no set to
validate a typo against. `goc --worker rodya` is legal input that
matches nothing, and no input-side guard can distinguish it from
`goc --worker rodja` on a deck where that worker holds no cards.

The output half of the contract covers it instead:
[empty-queue-view-prints-nothing-instead-of-saying-no-cards-match](../empty-queue-view-prints-nothing-instead-of-saying-no-cards-match/)
(done, 2026-08-04) made a zero-match table query state the filters it
matched on, so an unmatched `--worker` now echoes its value rather than
printing nothing. That is evidence for this card's framing, not a
substitute for it — it makes empty results *legible*, while the guards
tabulated above make invalid ones *impossible*. Whichever mechanism the
decision picks should say which of the two each flag gets, since at
least one flag can only have the second.

### The output half is opt-in per flag too — the same shape, one level down

[empty-result-line-reports-a-drained-ready-queue-that-still-has-cards](../empty-result-line-reports-a-drained-ready-queue-that-still-has-cards/)
(done, 2026-08-04) found the output half reproducing this card's own
thesis inside itself. `render_empty_query_line` names the filters in
effect from a **hand-maintained list parallel to `filter_cards`'
parameter list**, so a flag is described in a zero-match message only if
someone remembered to add a branch for it — precisely "opt-in per flag,
and new flags keep missing it". It had already drifted on arrival:
`--ready` was written as *replacing* the status clause though
`filter_cards` applies both, so `goc --ready --status done` omitted the
one filter that emptied the result.

Two consequences for the decision below:

1. **A contract table that registers only input rules leaves this
   drifting.** If option A is picked, the per-flag contract should be the
   single source for both halves — validator *and* how the flag names
   itself in a zero-match message — otherwise the next flag gets a
   validator and still goes unnamed on empty output. Under B or C the
   output enumeration stays hand-maintained with no fail-closed property
   at all.
2. **The output half can be wrong, not merely absent.** Every earlier
   instance in this family fails by staying silent — invalid input
   resolves to an empty result at exit 0. This one *asserted something
   false*: it reported the ready predicate had matched nothing while the
   same deck's plain `goc --ready` listed cards. A message derived from a
   filter set is a load-bearing claim about deck state, so "legible" is
   not a soft nice-to-have tier below "impossible" — an unguarded output
   half has its own failure mode, and it is worse than silence.

### And one conjunct can never have a flag — the dual of the `--worker` case

[empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card](../empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card/)
(done, 2026-08-11) found the third output-half instance, and it is the one
that constrains the mechanism rather than just adding a row.
`render_empty_query_line`'s hand-maintained enumeration is parallel to
`filter_cards`' **parameter** list, so it can only ever describe conjuncts
that *have* a parameter. The draft exclusion has none: `filter_cards` applies
`card_is_draft` unconditionally for every status but `all`, and `card_is_ready`
applies it a second time on its own axis, with nothing on the command line for
a parallel list to mirror. A deck whose only open cards were the ones `goc new`
had just written therefore printed the drained-deck sentence verbatim.

This is the exact dual of the `--worker` case above. There, a flag exists but
no input-side contract can cover it, so the output half has to. Here, the
output half is the *only* half there could be, because there is no flag to
attach a contract to at all.

Third consequence for the decision:

3. **A per-flag contract table is structurally blind to this class.** Option A
   registers contracts against flags; a conjunct with no flag has nothing to
   register. So whichever option is picked, the output-half enumeration needs
   to be driven by the predicate `filter_cards` actually applies, not by the
   flag list — otherwise the next unconditional conjunct added to the filter
   chain goes unnamed on empty output exactly as this one did, and a fail-closed
   property over flags will report full coverage while it happens.

## Decision required

Which mechanism replaces per-flag opt-in validation, and what severity
do unknown edge-filter titles get?

- **A — Central declarative flag-contract table.** Each query flag
  registers a contract (value validator; conflicts-with set; whether
  its argument must name an existing card). One pass in `_cmd_default`
  (after cards load, so title-existence checks are possible) enforces
  all contracts before filtering/rendering. A regression test walks the
  argparse parser and asserts every query flag has a contract entry —
  new flags fail closed. Most code, strongest guarantee; matches how
  the deck resolved the analogous families
  ([bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/),
  [draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it](../draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it/)).
- **B — argparse-native guards.** Mutually-exclusive group for
  `--board`/`--json`; `type=` validators where possible; a post-parse
  hook for deck-dependent checks (title existence). Less new machinery,
  but contracts stay scattered across the parser definition and the
  fail-closed property for future flags is weaker (nothing forces a new
  flag into a group or validator).
- **C — three more instance fixes.** Guard exactly the three instances
  above, no central mechanism. Cheapest now; the family history above
  is the argument against it.

Sub-decision for instance 1: hard error (exit 2, matching `--tag`) vs
stderr WARN + empty result (matching `compute_values`' dangling-edge
handling). Error is the family precedent; WARN keeps scripts that probe
for "does anything advance X?" working on renamed titles.

reproduce.py is fix-shape neutral: any probe that hard-errors OR emits
a diagnostic naming the offending flag/value counts as guarded.

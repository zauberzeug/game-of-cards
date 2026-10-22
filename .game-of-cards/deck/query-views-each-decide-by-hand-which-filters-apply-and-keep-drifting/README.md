---
title: query-views-each-decide-by-hand-which-filters-apply-and-keep-drifting
summary: "One goc query renders several views (table or JSON, board, ACTIVE banner, --ready leverage line, zero-match line), and each decides by hand which of the query's filters it honors. That choice has drifted six times, each found as its own card: five are fixed, yet --board still ignores every scope filter except --worker, and the ACTIVE banner ignores the same five with no recorded decision on whether that is deliberate. Make the query's scope one shared object every view reads, declare each deliberate exception, and guard it so a new view or a new filter cannot skip it."
status: open
stage: null
contribution: medium
created: "2026-10-08T05:20:41Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - active-card-banner-ignores-worker-filter
  - active-card-banner-tiebreak-undercounts-downstream-flow-under-worker-filter
  - board-worker-filter-hides-active-cards-by-applying-open-only-default
  - zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface
  - ready-leverage-line-compares-a-worker-scoped-pick-against-every-workers-gated-cards
  - board-view-silently-ignores-filters-other-than-status-and-worker
tags: [bug, meta-fix, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded on the per-view scope contract (which views read the query result, which read its scope under their own lifecycle rule, which are deliberately narrower, and why), including the board option from board-view-silently-ignores-filters-other-than-status-and-worker and whether the ACTIVE banner stays worker-only
  - [ ] TDD: reproduce.py exits 0, so every view honors every scope filter except the pairs its EXCEPTIONS set lists per the recorded decision
  - [ ] TDD: a regression test takes the scope-filter list from the shared scope object rather than a hand-kept copy, runs every view under each filter, and fails when a view ignores one without a declared exception
---

# The views of one `goc` query each decide by hand which filters apply, and keep drifting

## The pattern

`_cmd_default` (`goc/engine.py:4429`) answers one query and renders it
as several views in one invocation. The table and `--json` print the
query result. The `--board` grid, the `ACTIVE:` banner above the table,
the `--ready` leverage line below it, and the zero-match line each pick
their own set of cards. That set may be the result, the query's scope,
a hand-built partial scope, or the whole deck. Each choice is made at
its own site, and nothing checks it against the query. Six instances of
a view reading the wrong set were found and filed one at a time:

1. [active-card-banner-ignores-worker-filter](../active-card-banner-ignores-worker-filter/):
   the banner read the whole deck under `--worker`. The fix added a
   hand-built worker filter.
2. [board-worker-filter-hides-active-cards-by-applying-open-only-default](../board-worker-filter-hides-active-cards-by-applying-open-only-default/):
   the worker-scoped board took on the query's open-only status default
   and lost its other columns.
3. [active-card-banner-tiebreak-undercounts-downstream-flow-under-worker-filter](../active-card-banner-tiebreak-undercounts-downstream-flow-under-worker-filter/):
   the opposite direction. The scoped banner computed its tiebreak from
   the scoped subset, where it needed the full deck.
4. [zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface](../zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/):
   the zero-match line's draft recount replayed `filter_cards` alone,
   without the `--closed-since` and `--waiting` stages of the query.
5. [ready-leverage-line-compares-a-worker-scoped-pick-against-every-workers-gated-cards](../ready-leverage-line-compares-a-worker-scoped-pick-against-every-workers-gated-cards/):
   the leverage line's gated half read the whole deck while its
   "Pulling" half read the query.
6. [board-view-silently-ignores-filters-other-than-status-and-worker](../board-view-silently-ignores-filters-other-than-status-and-worker/),
   **live and decision-gated**: the board reads the whole deck unless
   `--status`, `--done` or `--worker` is given.

Six instances put the family past the four-instance meta-fix threshold.
Each fix landed at its own site, so the next view or the next filter
flag reopens the question.

## Location

All in `_cmd_default`, `goc/engine.py`:

| View | Reads today | Code |
|---|---|---|
| table, `--json` | query result | `:4539` `filtered = run_query()` |
| zero-match line | query result, drafts counted | `:4583` `run_query(include_drafts=True)` |
| leverage line, gated half | query scope, own lifecycle rule | `:4612` `filter_cards(cards, status=None, **scope)` |
| `--board` | whole deck unless `--status`, `--done` or `--worker` | `:4543` `board_cards = filtered if (status_filter_explicit or args.worker) else cards` |
| `ACTIVE:` banner | `--worker` only | `:4593` `notice_cards = ([t for t in cards if args.worker.lower() in ...] if args.worker else cards)` |

The `scope` dict at `:4482` holds stages, contribution, tags, advances,
advanced_by and worker. Instance 5's fix added it, and it is the first
shared piece. `run_query` and the leverage line read it. The board reads
it only when `--status`, `--done` or `--worker` is given, and the banner
never reads it.

## Empirical evidence

`reproduce.py` builds one temp deck per scope filter. Each deck holds a
ready, a gated and an active card inside the filter's scope and the same
three outside it. Out-of-scope titles start with `out-`, and the
out-of-scope gated card outranks the in-scope one. The script checks five
views of the same query. A view that names no card at all is an error,
not a pass, so no "honors" cell is vacuous. Output today:

```
filter         table     json      board     banner    leverage
--worker       honors    honors    honors    honors    honors
--tag          honors    honors    IGNORES   IGNORES   honors
--contribution honors    honors    IGNORES   IGNORES   honors
--stage        honors    honors    IGNORES   IGNORES   honors
--advances     honors    honors    IGNORES   IGNORES   honors
--advanced-by  honors    honors    IGNORES   IGNORES   honors

FAIL: 10 view/filter pair(s) drift from the query: board ignores --tag; banner ignores --tag; board ignores --contribution; banner ignores --contribution; board ignores --stage; banner ignores --stage; board ignores --advances; banner ignores --advances; board ignores --advanced-by; banner ignores --advanced-by
```

Against the engine before instance 5's fix (commit `70a41622`), the same
script shows the leverage column as IGNORES in all six rows.

## Why it matters

Each view is a claim about the same query, and readers act on whichever
line they read. `Skill(pull-card)` treats the banner as a soft-lock list
and the leverage line as a cue to ping a human. The board is the main
triage view. When one view leaves the query's scope, its reader gets an
answer to a question they did not ask, and nothing fails: every
instance above exited 0. Audits found each instance, no test did, and
each fix taught only its own site.

## Relationship to other meta cards

- [board-renderer-keeps-dropping-cards-the-table-shows](../board-renderer-keeps-dropping-cards-the-table-shows/)
  guards which cards `render_board` drops from the set it is handed.
  This card is about which set each view is handed. Instance 2 belongs
  to both cards.
- [draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it](../draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it/)
  has the same opt-in-per-surface shape, on the draft conjunct.
- [query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it](../query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it/)
  has it on flag validation.

## Decision required

**Reasoning.** Two contracts are open. The first is what each view
should read. Should the banner stay worker-only, as a soft-lock hint
where conflicting work can cross a tag boundary, or follow the whole
scope? And which of the options in
[board-view-silently-ignores-filters-other-than-status-and-worker](../board-view-silently-ignores-filters-other-than-status-and-worker/)
applies to the board? The second is whether the code should make that
choice once, in one place. Scripts and skills read these views, so both
are API behavior. Picking blindly either pins a bug into a guard or
changes what the banner tells a pull-card session.

### Option A: one query object, each view declares what it reads (recommended)

Build the scope and the lifecycle conjuncts once in `_cmd_default`. Each
view reads one of three things: the query result, the scope under its
own lifecycle rule, or the whole deck with a stated reason. A guard test
takes the filter list from the keys of `scope`, runs each view under
each filter, and fails on any ignore that is not declared.

- **Pros:** a new filter reaches every view the day it joins `scope`. A
  new view has to declare what it reads. The reproduce matrix becomes
  the regression test.
- **Cons:** touches every view in `_cmd_default`, and needs the board
  and banner contracts decided first.
- **Preview:** `goc/engine.py:4543` becomes
  `board_cards = filter_cards(cards, status=status, **scope)` (or the
  board option chosen). `:4593` becomes
  `filter_cards(cards, status=None, worker=args.worker)` with the
  banner's exception declared, or `filter_cards(cards, status=None, **scope)`.
  New test file `tests/test_query_views_share_scope.py`.

### Option B: guard only

Keep each view's hand-picked set, and pin the intended matrix in a test
with an explicit expected table.

- **Pros:** small. Documents the contract without moving code.
- **Cons:** a new view still picks by hand, and the guard knows only
  the views it lists. A new filter must be added to the test by hand.
- **Preview:** new `tests/test_query_views_share_scope.py` with an
  expected table. No engine change beyond the board card's own fix.

### Option C: keep fixing per instance

Close the board card on its own, and file the next instance when an
audit finds it.

- **Pros:** no new structure.
- **Cons:** the history above: six instances, each found by an audit.
- **Preview:** no code change.

**Recommendation:** Option A. The shared `scope` dict already exists,
and only the board and the banner still bypass it, so finishing the
move is smaller than the next one-site fix.
